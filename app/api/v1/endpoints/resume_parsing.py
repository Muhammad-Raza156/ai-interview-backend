from fastapi import APIRouter, HTTPException, Depends
from fastapi import UploadFile, File, Form
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from supabase import create_client, Client
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.user_management import ViewUser
from app.models.db_models import Resume
from app.utils.user_management import get_current_user
from app.schemas.resume_parsing import ParsedResume
from app.api.api_resonse import success_response
from app.utils.resume_parsing import process_pdf, resume_parsing_tempelate, llm_config, key_sections_tempelate
from app.models.db_models import JobDetails
from app.models.db_models import ResumeKeySections

from typing import List
from pydantic import BaseModel, Field


class KeySectionInfo(BaseModel):
    relevance_score: int = Field(..., ge=1, le=10, description="Score from 1-10 indicating relevance to job")
    key_points: List[str] = Field(..., description="List of important points to cover")
    required_knowledge: List[str] = Field(..., description="Specific knowledge areas to assess")
    candidate_experience: str = Field(..., description="Relevant experience from candidate's resume")
    suggested_focus: str = Field(..., description="Recommended focus areas for interview")

class InterviewSections(BaseModel):
    technical_skills: KeySectionInfo
    system_design: KeySectionInfo
    problem_solving: KeySectionInfo
    domain_knowledge: KeySectionInfo
    project_experience: KeySectionInfo


file_router = APIRouter()

#model_name = "command-r-plus-08-2024"
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@file_router.post("/submit-application")
async def submit_application(job_role: str = Form(...), industry: str = Form(...), company: str = Form(...),
                              description: str = Form(...), interview_type: str = Form(...), 
                             experience_level: str = Form(...),
                             file: UploadFile=File(...),
                             current_user: ViewUser = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db_session)):
    

    """
    Submits an application for a job, given the job role, industry, company, description, interview type, experience level, and a PDF file of the resume.

    Args:
        job_role (str): The role of the job.
        industry (str): The industry of the job.
        company (str): The company of the job.
        description (str): The description of the job.
        interview_type (str): The type of the interview.
        experience_level (str): The experience level of the job.
        file (UploadFile): The PDF file of the resume.

    Returns:
        dict: A JSON response with the URL of the uploaded resume.

    Raises:
        HTTPException: If there is an error with the file, or if there is a server error.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for the resume.")
    # save pdf to bucket on supabase

    user_id = current_user.user_id

    file_name = f"{user_id}_{file.filename}"
    folder_path = f"resumes/users/{user_id}/"

    try:
        job = JobDetails(user_id=user_id,role=job_role, industry=industry, 
                         company=company, experience_level=experience_level, 
                         description=description, interview_type=interview_type)
        try:

            db.add(job)
            await db.commit()
            await db.refresh(job)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


        # upload file to supabase bucket
        file_content = await file.read()

        response = supabase.storage.from_("resumes").upload(f"{folder_path}{file_name}", file_content)

        if  not response:
            raise HTTPException(status_code=500, detail="Failed to upload file to Supabase")
        
        file_url = supabase.storage.from_("resumes").get_public_url(f"{folder_path}{file_name}")

        return {"file":file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@file_router.post("/file")
async def file_parsing(current_user: ViewUser = Depends(get_current_user), 
                       db: AsyncSession = Depends(get_db_session)):
    
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

        
        response=supabase.storage.from_("resumes").list(path=folder_path)
        if not response:
            raise HTTPException(status_code=404, detail="No files found for this user.")
            
        file_name = response[0]['name']
        content= supabase.storage.from_("resumes").download(f"{folder_path}{file_name}")
        if  not content:
            raise HTTPException(status_code=404, detail="File not found.")

        resume_text = await process_pdf(content)
        if not resume_text.strip():
             raise HTTPException(status_code=400, detail="Extracted resume text is empty.")
        llm = await llm_config()
        output_parser = JsonOutputParser()
        resume_prompt = await resume_parsing_tempelate()
        try:
            chain1 = resume_prompt|llm|output_parser
            # run the chain
            processed_resume = await chain1.ainvoke({"resume_text": resume_text})
            #return {"data": processed_resume}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        # processed resume to json
        processed_resume_json = json.dumps(processed_resume)

        # Save the processed resume to the database
        parsed_resume = ParsedResume(user_id=user_id, parsed_sections=processed_resume_json)
        new_resume = Resume(**parsed_resume.dict())

        db.add(new_resume)
        await db.commit()
        await db.refresh(new_resume)        
        return {"data": processed_resume}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@file_router.post("/key-sections")
async def key_sections(current_user: ViewUser = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db_session)):
    user_id = current_user.user_id


    job_query = select(JobDetails).where(
        JobDetails.user_id == current_user.user_id
    )
    job_result = await db.execute(job_query)
    job_details = job_result.scalar_one_or_none()
    
    if not job_details:
        raise HTTPException(
            status_code=404,
            detail="Job details not found or not associated with current user"
        )

    stmt = select(Resume).where(Resume.user_id == user_id)
    resume_result = await db.execute(stmt)
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found for curent user or not uploaded")

    resume_data = json.loads(resume.parsed_sections) if isinstance(resume.parsed_sections, str) else resume.parsed_sections

    existing_sections_query = select(ResumeKeySections).where(
        ResumeKeySections.resume_id == resume.id,
        ResumeKeySections.job_id == job_details.id
    )
    existing_sections = await db.execute(existing_sections_query)
    existing_key_sections = existing_sections.scalar_one_or_none()
    
    if existing_key_sections:
        return {
            "status": "success",
            "data": {
                "job_role": job_details.role,
                "interview_sections": existing_key_sections.key_sections,
            },
            "message": "Retrieved existing interview sections"
        }
    
    llm = await llm_config()
    output_parser = JsonOutputParser(pydantic_object=InterviewSections)
    sections_prompt= await key_sections_tempelate()

    try:
        chain2 = sections_prompt|llm|output_parser
        # run the chain
        key_sections = await chain2.ainvoke({"job_role": job_details.role,
                                                "job_description": job_details.description,
                                                "resume_information": resume_data})
        
        
        new_key_sections = ResumeKeySections(
        resume_id=resume.id,
        job_id=job_details.id,
        job_role=job_details.role,
        key_sections=json.dumps(key_sections,indent=2)
        )
        db.add(new_key_sections)
        await db.commit()
        await db.refresh(new_key_sections)

        data = {
            "job_role": job_details.role,
            "interview_sections": key_sections
        }

        return success_response(data=data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


        
    


