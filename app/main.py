import uvicorn
from fastapi import FastAPI
from fastapi_pagination import add_pagination
import logging
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
from app.api.v1.endpoints.authentication import auth_router
from app.api.v1.endpoints.application import application_router
from app.api.v1.endpoints.profiling import profiling_route
from app.api.v1.endpoints.text_similarity import similarity_router
from app.api.v1.endpoints.user_management import user_router
from app.api.v1.endpoints.health import health_router
from app.api.v1.endpoints.interview import interview_router


from app.db.session import engine
from app.db.base import Base
from app.core.config import settings


class SensitiveInfoFilter(logging.Filter):
    def __init__(self, sensitive_keys):
        self.sensitive_keys = sensitive_keys

    def filter(self, record):
        for key in self.sensitive_keys:
            if key in record.getMessage():
                record.msg = record.msg.replace(key, "*****")
                record.args = ()
        return True


sensitive_keys = [
    "password",
    "access_token",
    "secret_key",
    "SECRET_KEY",
    "cohere_api_key",
    "database_url",
    "DB_PASSWORD",
    "DATABASE_URL",
    "DB_USER",
    "DB_URL",
    "SUPABASE_KEY",
    "SUPABASE_URL",
    "REDIS_PASSWORD",
    "REDIS_URL",
    "SECRET_KEY",
    "email",
    "SUPABASE_KEY",
    "SUPABASE_URL"
]
sensitive_data = SensitiveInfoFilter(sensitive_keys)

logger = logging.getLogger(__name__)

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)

logging.getLogger().addFilter(sensitive_data)

# Create the FastAPI app instance
app = FastAPI()

add_pagination(app)

origins = [
    "http://localhost:3001",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_version = settings.API_VERSION


# Database setup: Create tables
@app.on_event("startup")
async def create_tables():
    """
    Creates all tables in the database on application startup.

    This method is marked as an on_event("startup") function, which means it will be
    called once on application startup. The method uses the SQLAlchemy AsyncEngine
    to create all tables in the database. The tables are defined in the models submodule
    and are determined by the Base.metadata.create_all() call.

    :return: None
    """
    logger.info("Creating database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database connection established!")
            logger.info("Database tables created!")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    """
    Shuts down the database connection on application shutdown.

    This method is marked as an on_event("shutdown") function, which means it will be
    called once on application shutdown. The method uses the SQLAlchemy AsyncEngine
    to dispose of the database connection.

    :return: None
    """
    await engine.dispose()
    logging.info("Database connection closed!")
    logging.info("Application shutdown completed!")


# Include the example router
app.include_router(health_router, prefix=f"/api/v{api_version}")
app.include_router(auth_router, prefix=f"/api/v{api_version}", tags=["Authentication"])
app.include_router(user_router, prefix=f"/api/v{api_version}", tags=["User Management"])
app.include_router(
    application_router, prefix=f"/api/v{api_version}", tags=["Application"]
)
app.include_router(
    profiling_route, prefix=f"/api/v{api_version}", tags=["Profiling"]
)
app.include_router(
    similarity_router, prefix=f"/api/v{api_version}", tags=["Text Similarity"]
)
app.include_router(
    interview_router, prefix=f"/api/v{api_version}", tags=["Interview"]
)


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the AI Recruitment Tool API"}


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)