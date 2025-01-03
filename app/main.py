from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi_pagination import add_pagination
from app.api.v1.endpoints.authentication import auth_router
from app.api.v1.endpoints.resume_parsing import file_router as resume_router
from app.api.v1.endpoints.text_similarity import similarity_router
from app.api.v1.endpoints.user_management import user_router


from app.db.session import engine
from app.models.user import Base
from app.core.config import settings

# Create the FastAPI app instance
app = FastAPI()

add_pagination(app)

origins = [
    "http://localhost:3000",
    "http://0.0.0.0:3000",
    "http://localhost:8000",
    "http://0.0.0.0:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_version= settings.API_VERSION


# Database setup: Create tabless
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    print("Database connection closed!")

# Include the example router
app.include_router(auth_router, prefix=f"/api/v{api_version}", tags=["Authentication"])
app.include_router(user_router, prefix=f"/api/v{api_version}", tags=["User Management"])
app.include_router(resume_router, prefix=f"/api/v{api_version}", tags=["Resume Parsing"])
app.include_router(similarity_router, prefix=f"/api/v{api_version}", tags=["Text Similarity"])

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the AI Recruitment Tool API"}