from fastapi import (APIRouter, 
                     HTTPException, 
                     Depends,
                     WebSocket, 
                     WebSocketDisconnect,
                     WebSocketException)
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from langchain_core.output_parsers import JsonOutputParser
import jwt
import logging
from app.schemas.autentication import TokenData

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
    audio_to_text_silero,
    evaluation_tempelate,
    result_tempelate
)
from app.schemas.interview import *
from app.models.db_models import JobDetails
from app.models.db_models import User as UserModel
from app.models.db_models import ResumeKeySections

from redis import asyncio as aioredis
import platform
from typing import Dict


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
            settings.CACHE_EXPIRATION,
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
    
class InterviewWebSocketManager:
    def __init__(self):
        self.active_sessions: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_sessions[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_sessions:
            await self.active_sessions[user_id].send_json(message)

manager = InterviewWebSocketManager()

def decode_jwt(token: str):
    """Decodes the JWT token and returns the user data."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_email: str = payload.get("sub")
        return user_email
    except jwt.ExpiredSignatureError:
        raise WebSocketException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise WebSocketException(status_code=401, detail="Invalid token")

async def websocket_auth(websocket: WebSocket):
    """Extracts token from the WebSocket headers."""
    token = websocket.headers.get("Authorization")
    if not token:
        await websocket.close(code=1008)  # Close with policy violation code
        return None
    return token.replace("Bearer ", "")

@interview_router.websocket("/ws/interview")
async def websocket_interview(
    websocket: WebSocket, 
    db: AsyncSession = Depends(get_db_session)
):

    """
    Handles the WebSocket connection for the interview process.

    This endpoint is used to communicate with the client during the interview process.
    It receives messages from the client and sends messages to the client to update the
    UI. The messages are processed in the order they are received and are used to update
    the database with the user's answers.

    Args:
        websocket (WebSocket): The WebSocket object representing the connection to the client.
        db (AsyncSession): The database session dependency.

    Returns:
        None
    """

    token = await websocket_auth(websocket)
    if not token:
        await websocket.close(code=4001, detail="Unauthorized")
        return
    user_email = decode_jwt(token)
    token_data = TokenData(user_email=user_email)
    stmt = select(UserModel).where(UserModel.email == token_data.user_email)
    response = await db.execute(stmt)
    if not response:
        raise WebSocketException(status_code=404, detail="User not found")
    db_user = response.scalar_one_or_none()

    user_id = db_user.user_id
    await manager.connect(websocket, user_id)

    try:
        cache_key = f"interview_questions:{user_id}"
        cached_data = await redis_client.get(cache_key)

        if not cached_data:
            await manager.send_message(user_id,
                                    { 
                                        "type": "error",
                                        "message": "Interview questions not found. Please generate questions first."
                                        })
            return

        cached_data = json.loads(cached_data)
        questions = cached_data["questions"]

        evaluation_prompt = await evaluation_tempelate()
        evaluation_llm = await llm_config(temperature=0.3)
        evaluation_parser = JsonOutputParser(pydantic_object=EvaluationResult)

        # Create a new interview session in the database
        session = InterviewSession(
            user_id=user_id,
            job_role=cached_data["job_role"],
            status='active'
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Send session start message
        await manager.send_message(user_id, {
                "type": "session_start",
                "session_id": session.id,
                "job_role": cached_data["job_role"]
            })

        result=[]
        for section in questions.keys():
            await manager.send_message(user_id, {
                "type": "section_start",
                "section": section
            })
            
            for question_data in questions[section]:
                text = question_data["question"]
                model_answer = question_data["answer"]

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

                # Send question to client
                await manager.send_message(user_id, {
                    "type": "question",
                    "question_id": question.id,
                    "text": text
                })
                try:
                    audio_response = await websocket.receive_bytes()
                    candidate_answer = await audio_to_text_silero(audio_response)

                    # Evaluate response using LLM
                    evaluation_chain = evaluation_prompt | evaluation_llm | evaluation_parser
                    evaluation_result = await evaluation_chain.ainvoke({
                        "question": text,
                        "candidate_answer": candidate_answer,
                        "model_answer": model_answer,
                    })

                    score = evaluation_result["score"]
                    feedback = evaluation_result["feedback"]

                    # Save response in the database
                    answer = Answer(
                        session_id=session.id,
                        question_id=question.id,
                        user_answer=candidate_answer,
                        score=int(score),
                        feedback=json.dumps(feedback)
                    )
                    db.add(answer)
                    await db.commit()
                    #await db.refresh()

                    # Send evaluation result to client
                    await manager.send_message(user_id, {
                            "type": "evaluation",
                            "question_id": question.id,
                            "transcribed_answer": candidate_answer,
                            "score": score,
                            "feedback": feedback
                        })
                    
                    result.append({
                            "section": section,
                            "result": evaluation_result
                        })
                except Exception as e:
                        logger.error(f"Error processing answer: {str(e)}")
                        await manager.send_message(user_id, {
                            "type": "error",
                            "message": "Error processing answer"
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
            settings.CACHE_EXPIRATION,
            json.dumps(data)
        )

        await manager.send_message(user_id, {
            "type": "complete",
            "data": data
        })
        #await websocket.close()

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {user_id}")
        if 'session' in locals():
            session.status = 'incomplete'
            await db.commit()

    except Exception as e:
        logger.error(f"Error in interview process: {str(e)}")
        await manager.send_message(user_id, {
            "type": "error",
            "message": str(e)
        })
    
    finally:
        manager.disconnect(user_id)


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