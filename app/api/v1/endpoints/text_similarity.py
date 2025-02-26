from fastapi import APIRouter, HTTPException, Depends
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import cohere

from app.db.session import get_db_session
from app.models.db_models import JobDetails, Resume
from app.utils.user_management import get_current_user
from app.schemas.user_management import ViewUser
from app.core.config import settings
from app.api.api_resonse import error_response, success_response

similarity_router = APIRouter()
co=cohere.ClientV2(settings.COHERE_API_KEY)


def calculate_similarity(text1, text2):
    docs=[text1,text2]

    embeddings1 = co.embed(texts=docs, 
                         model='embed-english-v3.0', 
                         input_type="search_document",
                         embedding_types=["float"]).embeddings.float
    
    embedding1 = [embeddings1[0]]
    embedding2 = [embeddings1[1]]
    
    similarity = cosine_similarity(embedding1, embedding2)[0][0]

    return similarity




@similarity_router.get("/similarity")
async def text_similarity(current_user: ViewUser = Depends(get_current_user), 
                          db: AsyncSession = Depends(get_db_session)):
    """
    Retrieves the job details and resume associated with the current user.

    This endpoint retrieves the job role, experience level, and description of the job
    associated with the current user. It also retrieves the parsed sections of the resume
    associated with the current user. The endpoint then calculates the similarity between
    the job description and the parsed sections of the resume and returns the similarity score.

    Args:
        current_user (ViewUser): The current authenticated user.
        db (AsyncSession): The database session dependency.

    Returns:
        JSON: A success response containing the similarity score if successfully retrieved.

    Raises:
        HTTPException: If job details or resume are not found or associated with the current user,
                       or if there is a server error during processing.
    """

    user_id = current_user.user_id
    stmt = select(JobDetails.role, 
                  JobDetails.experience_level ,
                  JobDetails.description).where(JobDetails.user_id == user_id)
    result = await db.execute(stmt)
    job_details = result.first()

    if not job_details:
        raise HTTPException(status_code=404, detail="Job details not found or not associated with current user")

    role = job_details.role
    experience_level = job_details.experience_level
    description = job_details.description

    stmt2 = select(Resume.parsed_sections).where(Resume.user_id == user_id)
    result2 = await db.execute(stmt2)
    resume = result2.first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found or not associated with current user")

    data = resume.parsed_sections
    # convert data to str 
    data = " ".join(data)

    try: 

        simialarity_score=calculate_similarity(description,data)

        
        return success_response(data=simialarity_score)
    except Exception as e:
        raise error_response(message=str(e))
