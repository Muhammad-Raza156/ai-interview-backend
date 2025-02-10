from fastapi import APIRouter, HTTPException, Depends
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from langchain_core.output_parsers import JsonOutputParser
import logging

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.user_management import ViewUser
from app.models.db_models import (
    Resume, 
    InterviewSession,
    Question,
    Answer
) 
from app.utils.user_management import get_current_user
from app.api.api_resonse import success_response
from app.utils.resume_parsing import (
    llm_config,
)
from app.utils.interview import (
    questions_tempelate,
    tts_speak,
    record_audio,
    audio_to_text_silero,
    record_audio_with_stop,
    evaluation_tempelate,
    result_tempelate,
    OverallResult
)
from app.models.db_models import JobDetails
from app.models.db_models import ResumeKeySections

from typing import List, Optional
from pydantic import BaseModel, Field

from redis import asyncio as aioredis
import platform
import tempfile
import os


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

interview_router = APIRouter()

@interview_router.post("/generate-interview-questions")
async def generate_questions(
    current_user: ViewUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generates interview questions for the current user's job application.

    This function generates a set of interview questions based on the user's job details,
    resume data, and existing key sections. It utilizes a language model to generate
    questions tailored to the job role and description, and the generated questions
    for the current user saved to redis cache for later use.

    Args:
        current_user (ViewUser): The current authenticated user.
        db (AsyncSession): The database session dependency.

    Returns:
        JSON: A success response containing the job role and generated interview questions.

    Raises:
        HTTPException: If job details, resume, or key sections are not found for the current user,
                       or if there is an error during question generation.
    """

    logger.info("Generating interview questions...")
    user_id = current_user.user_id

    job_query = select(JobDetails).where(JobDetails.user_id == current_user.user_id).order_by(
        desc(JobDetails.created_at)).limit(1)
    job_result = await db.execute(job_query)
    job_details = job_result.scalar_one_or_none()

    if not job_details:
        logger.error("Job details not found or not associated with current user")
        raise HTTPException(
            status_code=404,
            detail="Job details not found or not associated with current user",
        )

    resume_query = select(Resume).where(Resume.user_id == user_id)
    resume_result = await db.execute(resume_query)
    resume = resume_result.scalar_one_or_none()

    if not resume:
        logger.error("Resume not found or not associated with current user")
        raise HTTPException(status_code=404, detail="Resume not found")
    
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

    if not existing_key_sections:
        raise HTTPException(status_code=404, detail="Key sections not found")
    
    try:
        questions_prompt = await questions_tempelate()
        llm = await llm_config(temperature=0.7)
        OutputParser  = JsonOutputParser(pydantic_object=SectionQuestions)

        chain = questions_prompt | llm | OutputParser
        questions = await chain.ainvoke({
            "job_role": job_details.role,
            "job_description": job_details.description,
            "resume_data": resume_data,
            "interview_sections": existing_key_sections.key_sections,
        })

        cache_key = f"interview_questions:{user_id}"
        await redis_client.setex(
            cache_key,
            CACHE_EXPIRATION,
            json.dumps({
                "questions": questions,
                "job_role": job_details.role
            })
        )

        return success_response(data={
            "job_role": job_details.role,
            "interview_questions": questions
        })

    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@interview_router.post("/interview-session")
async def conduct_interview(
    current_user: ViewUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):

    """
    Conducts an interview session for the current user based on pre-generated questions.

    This endpoint initiates an interview session using  interview questions stored in redis cache for the
    authenticated user. It evaluates the user's answers against model answers to compute 
    scores and feedback. The session details, including questions, answers, scores, and 
    feedback, are stored in the database.

    Args:
        current_user (ViewUser): The current authenticated user.
        db (AsyncSession): The database session dependency.

    Returns:
        JSON: A success response containing the job role, interview questions, and evaluation results.

    Raises:
        HTTPException: If interview questions are not found in the cache, or if there is an error during processing.
    """

    user_id = current_user.user_id

    cache_key = f"interview_questions:{user_id}"
    cached_data = await redis_client.get(cache_key)

    evaluation_prompt = await evaluation_tempelate()
    evaluation_llm = await llm_config(temperature=0.3)
    evaluation_parser = JsonOutputParser(pydantic_object=EvaluationResult)

    try:
        if not cached_data:
            raise HTTPException(
                status_code=404,
                detail="Interview questions not found. Please generate questions first."
            )
        
        cached_data = json.loads(cached_data)
        questions = cached_data["questions"]

        sections= questions.keys()
        result=[]
        print("Session started")
        session = InterviewSession(
            user_id=user_id,
            job_role=cached_data["job_role"],
            status='active'
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        for section in sections:
            print("session in progress")
            tts_speak(f"Section: {section}")
            for i in range(len(questions.get(section))):
                text=questions.get(section)[i]["question"]
                model_answer=questions.get(section)[i]["answer"]

                if isinstance(model_answer, list):
                    model_answer = "\n".join(model_answer)

                question = Question(
                session_id=session.id,
                question_text=text,
                model_answer=model_answer
            )
                
                db.add(question)
                await db.commit()
                await db.refresh(question)

                print(text)
                tts_speak(text)
                #print("Starting audio recording session...")
                logger.info("Starting audio recording session...")
                #candidate_answer=record_audio_with_stop()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
                    audio_filename = temp_audio_file.name
                record_audio(audio_filename)  # Record audio and save to file

                # Convert recorded audio to text using Silero
                candidate_answer = await audio_to_text_silero(audio_filename)

                try:
                    os.remove(audio_filename)
                    logger.info(f"Temporary audio file {audio_filename} removed.")
                except Exception as e:
                    logger.error(f"Error removing temporary audio file: {e}")

                evaluation_chain = evaluation_prompt | evaluation_llm | evaluation_parser
                evaluation_result = await evaluation_chain.ainvoke(
                    {
                        "question": text,
                        "candidate_answer": candidate_answer,
                        "model_answer": model_answer,
                    }
                )
                score = evaluation_result["score"]
                feedback = evaluation_result["feedback"]
                answer = Answer(
                session_id=session.id,
                question_id=question.id,
                user_answer=candidate_answer,
                score=int(score),
                feedback=json.dumps(feedback)
            )
                db.add(answer)
                await db.commit()
                await db.refresh(question)
                result.append({
                    "section":section, 
                    "result":evaluation_result
                    })

        session.status = 'completed'
        await db.commit()

        data = {
            "job_role": cached_data["job_role"], 
            "interview_questions": questions, 
            "evaluation_result": result
            }
        result_cache_key = f"evaluation_result:{user_id}"
        await redis_client.setex(
            result_cache_key, 
            CACHE_EXPIRATION, 
            json.dumps(data)
        )
        logger.info("data saved successfully to database")
        return success_response(data=data)

    except Exception as e:
        logger.error(f"Error in interview process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@interview_router.get("/result")
async def get_user_result(current_user: ViewUser = Depends(get_current_user)):
    """
    Retrieves the overall interview result for the current user.

    This function fetches the cached interview evaluation result data for the current user
    from the Redis cache. It then processes this data to compute the overall interview 
    result using a language model and a result template.

    Args:
        current_user (ViewUser): The current authenticated user.

    Returns:
        dict: A dictionary containing the user ID and the overall interview result.

    Raises:
        HTTPException: If the user data is not found in the cache.
    """

    user_id = current_user.user_id
    cache_key = f"evaluation_result:{user_id}"
    user_data = await redis_client.get(cache_key)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User data not found")
    
    # Deserialize the data from JSON
    user_data = json.loads(user_data)

    questions = user_data["interview_questions"]
    results = user_data["evaluation_result"]

    result_prompt = await result_tempelate()
    result_llm = await llm_config(temperature=0.1)

    result_parser = JsonOutputParser(pydantic_object=OverallResult)
    chain3 = result_prompt | result_llm | result_parser
    overall_result = await chain3.ainvoke({
        "questions":questions, 
         "results":results
    })
    return {"user_id": user_id, "overall_result": overall_result}