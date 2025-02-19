from app.core.celery import celery_app
from sqlalchemy.orm import Session
import celery
from sqlalchemy import create_engine, select
from app.utils.resume_parsing import ( 
    process_pdf, 
    resume_parsing_template, 
    llm_config
)
import json
from app.models.db_models import Resume
from langchain_core.output_parsers import JsonOutputParser
from uuid import UUID
import logging
import asyncio
from app.core.config import settings
from sqlalchemy.pool import QueuePool
from app.schemas.application import ParsedResume


logger = logging.getLogger(__name__)

database_url = f"postgresql+psycopg2://postgres.reyyarznpztvshewnmji:{settings.DB_PASSWORD}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

engine = create_engine(database_url,
                       pool_size=10,
                       max_overflow=10,
                       pool_timeout=300,
                       pool_pre_ping=True,
                       pool_recycle=3600,
                       poolclass=QueuePool,
                       echo=True)

@celery_app.task(name="process_file", max_retries=3)
def process_file(file_content: bytes, user_id: UUID):
    """
    Processes a resume file by extracting text, parsing it, and saving the parsed data to the database.

    This Celery task handles the processing of a resume file in PDF format. It performs the following steps:
    1. Extracts text from the PDF using OCR.
    2. Creates a resume parsing template to structure the extracted text.
    3. Configures a language model to parse the structured text.
    4. Processes the resume text using a chain of operations (language model, template, parser).
    5. Saves the processed resume data to the database.

    Args:
        file_content (bytes): The byte content of the PDF file.
        user_id (UUID): The unique identifier of the user associated with the resume.

    Returns:
        dict: A dictionary containing the processed resume data and the status of the operation.
        If successful, returns the saved resume data and a success status.
        If an error occurs, returns the error message and a failed status.

    Raises:
        ValueError: If the extracted resume text is empty.
    """
    try:
        
        async def async_task(file_content):
            # Step 1: Extract text from the PDF
            resume_text = await process_pdf(file_content)

            if not resume_text.strip():
                logger.error("Extracted resume text is empty.")
                raise ValueError("Extracted resume text is empty.")

            # Step 2: Create the resume parsing template
            prompt = await resume_parsing_template()
            output_parser = JsonOutputParser()

            # Step 3: Configure the LLM
            llm = await llm_config()

            # Step 4: Create the chain
            chain = prompt| llm | output_parser        

            # Step 5: Process the resume text using the chain
            processed_resume = await chain.ainvoke({"resume_text":resume_text})

            return processed_resume
        processed_resume = asyncio.run(async_task(file_content))
        processed_resume_json=json.dumps(processed_resume)
        #print("Resume parsing completed successfully")
        logger.info("Resume parsing completed successfully")

        with Session(engine) as db:
            try:
                # Example: Save data to the database

                existing_resume = db.execute(
                    select(Resume).where(Resume.user_id == user_id)
                ).scalars().first()
                if existing_resume:
                    existing_resume.parsed_sections = processed_resume_json
                    logger.info(f"Resume updated for user_id={user_id}")
                else:
                    parsed_resume = ParsedResume(
                        user_id=user_id, parsed_sections=processed_resume_json
                    )
                    existing_resume = Resume(**parsed_resume.dict())
                    db.add(existing_resume)
                    logger.info(f"New resume inserted for user_id={user_id}")
                db.commit()
                db.refresh(existing_resume)
                

                #save to redis cache
                cache_key = f"user_{user_id}_resume"
                celery_app.backend.set(cache_key, 
                                       processed_resume_json, 
                                       expires=settings.CACHE_EXPIRATION)
                return {"data": existing_resume.parsed_sections, 
                        "status": "success"}
            except Exception as e:
                db.rollback()
                if "server closed the connection unexpectedly" in str(e):
                    raise celery.Task.retry(exc=e, countdown=2 ** celery.Task.request.retries)
                logger.error(f"Error saving data to the database: {str(e)}")
                return {"error": str(e), "status": "failed"}
    except Exception as e:
        # Log the error
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        # Return a meaningful result
        return {"error": str(e), "status": "failed"}