from fastapi import APIRouter, Depends, HTTPException
import platform
from redis import asyncio as aioredis
import logging
import json
from sqlalchemy import desc, select

from app.core.config import settings
from app.db.session import get_db_session
from app.utils.user_management import get_current_user
from app.schemas.user_management import ViewUser
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.profiling import prompt, OutputParser
from app.utils.resume_parsing import llm_config
from app.models.db_models import JobDetails, Resume
from app.core.celery import celery_app


logger = logging.getLogger(__name__)


if platform.system() == "Windows":
    redis_client = aioredis.Redis(
        host="localhost", 
        port=settings.REDIS_PORT, 
        password=settings.REDIS_PASSWORD, db=0, 
        decode_responses=True)
else:
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        db=0
    )
CACHE_EXPIRATION = 3600

profiling_route = APIRouter()


@profiling_route.get("/profiling")
async def get_profiling(user: ViewUser = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db_session)):
    
    user_id = user.user_id
    # Get the user's profiling data like resume, job details from the redis cache
    job_key=f"user_{user_id}_job"
    job_data = await redis_client.get(job_key)
    if job_data is not None:
        job_data = json.loads(job_data)
    else:
        job_query = select(
            JobDetails.role, JobDetails.description
            ).where(JobDetails.user_id ==user_id).order_by(
        desc(JobDetails.created_at)).limit(1)
        job_result = await db.execute(job_query)
        job = job_result.fetchone()
        if not job:
            logger.error("Job details not found or not associated with current user")
            raise HTTPException(status_code=404, detail="Job details not found")
        else:
            job_data = {
                "role": job[0],
                "description": job[1]
            }
    
    resume_key=f"user_{user_id}_resume"
    resume_data = await redis_client.get(resume_key)
    if resume_data is not None:
        resume_data = json.loads(resume_data)
    elif resume_data is None:
        resume_data=celery_app.backend.get(resume_key)
        if resume_data is not None:
            resume_data = json.loads(resume_data)
        else:
            resume_query = select(Resume).where(Resume.user_id == user_id)
            resume_result = await db.execute(resume_query)
            resume = resume_result.scalar_one_or_none()
            if not resume:
                logger.error("Resume not found or not associated with current user")
                raise HTTPException(status_code=404, detail="Resume not found")
            else:
                resume_data = (
                    json.loads(resume.parsed_sections)
                    if isinstance(resume.parsed_sections, str)
                    else resume.parsed_sections
                )
        
    # Get the job details from the database
    if job_data:
        job_role = job_data['role']
        job_description = job_data['description']
    else:
        logger.error("Job details not found or not associated with current user")
        raise HTTPException(status_code=404, detail="Job details not found")

    # Get the resume data from the database

    llm = await llm_config(temperature=0.3)
    profiling_chain = prompt | llm | OutputParser
    
    try:
        profiling_result = await profiling_chain.ainvoke(
            {
                "resume_text": resume_data,
                "job_role": job_role,
                "job_description": job_description 
             }
            )
        return {"profiling_result": profiling_result}
    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        raise HTTPException(status_code=500, detail="Profiling failed")