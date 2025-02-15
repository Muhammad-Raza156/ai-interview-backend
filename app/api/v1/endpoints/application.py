from fastapi import APIRouter, HTTPException, Depends
from fastapi import UploadFile, File, Form
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from supabase import create_client, Client
from langchain_core.output_parsers import JsonOutputParser
import logging

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.tasks import process_file
from app.db.session import get_db_session
from app.schemas.user_management import ViewUser
from app.models.db_models import (
    Resume
) 
from app.utils.user_management import get_current_user
from app.schemas.application import ParsedResume, JobInterviewForm
from app.api.api_resonse import success_response
from app.utils.resume_parsing import (
    process_pdf,
    resume_parsing_template,
    llm_config,
    key_sections_tempelate
)
from app.models.db_models import JobDetails
from app.models.db_models import ResumeKeySections

from typing import List, Optional
from pydantic import BaseModel, Field

from redis import asyncio as aioredis
import platform

class KeySectionInfo(BaseModel):
    relevance_score: int = Field(
        ..., ge=1, le=10, description="Score from 1-10 indicating relevance to job"
    )
    key_points: List[str] = Field(..., description="List of important points to cover")
    required_knowledge: List[str] = Field(
        ..., description="Specific knowledge areas to assess"
    )
    candidate_experience: str = Field(
        ..., description="Relevant experience from candidate's resume"
    )
    suggested_focus: str = Field(
        ..., description="Recommended focus areas for interview"
    )


class InterviewSections(BaseModel):
    technical_skills: KeySectionInfo
    system_design: KeySectionInfo
    problem_solving: KeySectionInfo
    domain_knowledge: KeySectionInfo
    project_experience: KeySectionInfo

class QuestionDetail(BaseModel):
    question: str = Field(..., description="The interview question")
    model_answer: str = Field(
        ...,
        description="Complete model answer that demonstrates ideal response",
        min_length=50
    )
    expected_answer_points: List[str] = Field(..., description="Key points that should be covered in the answer")

class SectionQuestions(BaseModel):
    technical_knowledge: List[QuestionDetail] = Field(..., 
                                                      description="Questions about technical skills and knowledge")
    system_design: List[QuestionDetail] = Field(..., 
                                                description="System design and architecture questions")
    problem_solving: List[QuestionDetail] = Field(..., 
                                                  description="Algorithmic and logical problem-solving questions")
    coding_challenge: List[QuestionDetail] = Field(..., 
                                                   description="Programming implementation questions")


class Feedback(BaseModel):
    type: str = Field(
        ..., 
        description="Type of feedback: 'positive' or 'negative'",
        pattern='^(positive|negative)$'
    )
    points: List[str] = Field(
        ...,
        description="List of feedback points",
        min_items=1
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Improvement suggestions when feedback is negative"
    )
    missing_points: Optional[List[str]] = Field(
        default=None,
        description="Points that were missing from the answer"
    )

class EvaluationResult(BaseModel):
    score: float = Field(
        ...,
        description="Score out of 10",
        ge=0,
        le=10
    )
    feedback: Feedback = Field(
        ...,
        description="Structured feedback containing positive/negative points and suggestions"
    )


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

application_router = APIRouter()

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@application_router.post("/submit-application")
async def submit_application(
    job_role: str = Form(...),
    industry: str = Form(...),
    company: str = Form(...),
    description: str = Form(...),
    interview_type: str = Form(...),
    experience_level: str = Form(...),
    file: UploadFile = File(...),
    current_user: ViewUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Submits a job application with a resume in PDF format and returns the public URL of the uploaded file.

    The endpoint expects a form with the following fields:
    - job_role: The role the user is applying for.
    - industry: The industry of the job.
    - company: The company of the job.
    - description: The description of the job.
    - interview_type: The type of interview the user is applying for.
    - experience_level: The experience level of the user.
    - file: The resume file in PDF format.

    The endpoint first checks if the file is in PDF format. If not, it raises an HTTPException.

    It then saves the job details to the database and extracts text from the PDF using OCR.
    The extracted text is then further processed to extract relevant resume information such as
    skills, work experience, projects, and education using the Cohere model.

    Finally, the endpoint uploads the PDF file to the Supabase bucket and returns the public URL of the uploaded file.
    """
    if file.content_type != "application/pdf":
        logger.error("Only PDF files are allowed for the resume.")
        raise HTTPException(
            status_code=400, detail="Only PDF files are allowed for the resume."
        )
    

    user_id = current_user.user_id

    # save pdf to bucket on supabase
    file_name = f"{user_id}_{file.filename}"
    folder_path = f"resumes/users/{user_id}/"
    file_path = f"{folder_path}{file_name}"

    try:

        file_content = await file.read()
        logger.info("File content read successfully")
        existing_job = await db.execute(
        select(JobDetails).where(
            JobDetails.user_id == user_id,
            JobDetails.role == job_role,
            JobDetails.company == company,
            JobDetails.experience_level == experience_level,
            JobDetails.description == description
            )
        )
        existing_job = existing_job.scalar_one_or_none()

        if not existing_job:
            job = JobDetails(
                user_id=user_id,
                role=job_role,
                industry=industry,
                company=company,
                experience_level=experience_level,
                description=description,
                interview_type=interview_type,
            )
            try:
                

                # save job details to redis cache
                await redis_client.set(
                    f"user_{user_id}_job",
                    json.dumps({
                        "role": job_role,
                        "description": description
                    }),
                    ex=CACHE_EXPIRATION
                )
                logger.info("Job details saved to Redis cache")
                db.add(job)
                await db.commit()
                await db.refresh(job)
                logger.info("Job details saved successfully to database")
            except Exception as e:
                logger.error(f"Error saving job details to database: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        else:
            logger.info("Job with the same details already exists. Skipping insertion.")
        
        task = process_file.delay(file_content, user_id)
        print(f"Task ID: {task.id}")

        # Check if the file already exists
        existing_files = supabase.storage.from_("resumes").list(folder_path)
        existing_filenames = [file_info["name"] for file_info in existing_files]
        if file_name in existing_filenames:
            # Delete the existing file
            delete_response = supabase.storage.from_("resumes").remove([file_path])
            if not delete_response:
                logger.error("Failed to delete existing file from Supabase")
                raise HTTPException(
                    status_code=500, detail="Failed to delete existing file from Supabase"
                )

        # upload file to supabase bucket
        response = supabase.storage.from_("resumes").upload(
            file_path, file_content
        )

        if not response:
            logger.error("Failed to upload file to Supabase")
            raise HTTPException(
                status_code=500, detail="Failed to upload file to Supabase"
            )

        file_url = supabase.storage.from_("resumes").get_public_url(
            f"{folder_path}{file_name}"
        )

        logger.info(f"File uploaded to Supabase successfully at {file_url}")

        return {"file": file_url}
    except Exception as e:
        logger.error(f"Error uploading file to Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@application_router.post("/file")
async def file_parsing(
    current_user: ViewUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves and processes a user's resume file stored in Supabase storage.

    This function retrieves the first resume file associated with the current user
    from the Supabase storage. It then processes the PDF file to extract text,
    and further processes the text to extract relevant resume information such as
    skills, work experience, projects, and education using the Cohere model.

    Args:
        current_user (ViewUser): The current user authenticated and retrieved from
        the token.

    Raises:
        HTTPException: If no files are found for the user, if the file cannot be
        downloaded, or if any other error occurs during processing.

    Returns:
        dict: A dictionary containing the extracted relevant resume information.
    """
    try:
        user_id = current_user.user_id

        folder_path = f"resumes/users/{user_id}/"

        response = supabase.storage.from_("resumes").list(path=folder_path)
        if not response:
            logger.error("No files found for this user.")
            raise HTTPException(status_code=404, detail="No files found for this user.")

        file_name = response[0]["name"]
        content = supabase.storage.from_("resumes").download(
            f"{folder_path}{file_name}"
        )
        if not content:
            logger.error(f"File not found.")
            raise HTTPException(status_code=404, detail="File not found.")

        resume_text = await process_pdf(content)
        if not resume_text.strip():
            logger.error("Extracted resume text is empty.")
            raise HTTPException(
                status_code=400, detail="Extracted resume text is empty."
            )
        llm = await llm_config()
        output_parser = JsonOutputParser()
        resume_prompt = await resume_parsing_template()
        try:
            chain1 = resume_prompt | llm | output_parser
            # run the chain
            processed_resume = await chain1.ainvoke({"resume_text": resume_text})
            logger.info("Resume parsing completed successfully")
        except Exception as e:
            logger.error(f"Error parsing resume: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        # processed resume to json
        processed_resume_json = json.dumps(processed_resume)
        await redis_client.set(
                    f"user_{user_id}_resume",
                    processed_resume_json,
                    ex=CACHE_EXPIRATION
                )

        # Save the processed resume to the database
        parsed_resume = ParsedResume(
            user_id=user_id, parsed_sections=processed_resume_json
        )
        new_resume = Resume(**parsed_resume.dict())

        db.add(new_resume)
        await db.commit()
        await db.refresh(new_resume)
        logger.info("Resume parsed and saved successfully to database")
        return {"data": processed_resume}

    except Exception as e:
        logger.error(f"Error parsing resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@application_router.post("/key-sections")
async def key_sections(
    current_user: ViewUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generates and retrieves key interview sections for a job application.

    This endpoint processes a submitted resume and job details to extract or
    generate key sections relevant for a job interview, such as technical skills,
    system design, problem solving, domain knowledge, and project experience.

    Args:
        current_user (ViewUser): The current authenticated user.
        db (AsyncSession): The database session dependency.

    Returns:
        JSON: A success response containing the job role and interview sections
              if successfully retrieved or generated.

    Raises:
        HTTPException: If job details or resume are not found or associated with
                       the current user, or if there is an error during processing.
    """

    user_id = current_user.user_id

    job_query = select(JobDetails).where(JobDetails.user_id == current_user.user_id).order_by(
        JobDetails.created_at.desc()
    ).limit(1)
    job_result = await db.execute(job_query)
    job_details = job_result.scalar_one_or_none()

    if not job_details:
        logger.error("Job details not found or not associated with current user")
        raise HTTPException(
            status_code=404,
            detail="Job details not found or not associated with current user",
        )

    stmt = select(Resume).where(Resume.user_id == user_id)
    resume_result = await db.execute(stmt)
    resume = resume_result.scalar_one_or_none()
    if not resume:
        logger.error("Resume not found for curent user or not uploaded")
        raise HTTPException(
            status_code=404, detail="Resume not found for curent user or not uploaded"
        )

    resume_data = (
        json.loads(resume.parsed_sections)
        if isinstance(resume.parsed_sections, str)
        else resume.parsed_sections
    )

    existing_sections_query = select(ResumeKeySections).where(
        ResumeKeySections.resume_id == resume.id,
        ResumeKeySections.job_id == job_details.id,
    )
    existing_sections = await db.execute(existing_sections_query)
    existing_key_sections = existing_sections.scalar_one_or_none()

    if existing_key_sections:
        logger.info("Retrieved existing interview sections")
        return {
            "status": "success",
            "data": {
                "job_role": job_details.role,
                "interview_sections": existing_key_sections.key_sections,
            },
            "message": "Retrieved existing interview sections",
        }

    llm = await llm_config()
    output_parser = JsonOutputParser(pydantic_object=InterviewSections)
    sections_prompt = await key_sections_tempelate()

    try:
        chain2 = sections_prompt | llm | output_parser
        # run the chain
        key_sections = await chain2.ainvoke(
            {
                "job_role": job_details.role,
                "job_description": job_details.description,
                "resume_information": resume_data,
            }
        )

        logger.info("Key sections generated successfully")
        new_key_sections = ResumeKeySections(
            resume_id=resume.id,
            job_id=job_details.id,
            job_role=job_details.role,
            key_sections=json.dumps(key_sections, indent=2),
        )
        db.add(new_key_sections)
        await db.commit()
        await db.refresh(new_key_sections)

        data = {"job_role": job_details.role, "interview_sections": key_sections}
        logger.info("data saved successfully to database")
        return success_response(data=data)

    except Exception as e:
        logger.error(f"Error generating key sections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
