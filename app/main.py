from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from app.api.v1.endpoints.example import router as example_router  # Import your router
from app.db.session import engine
from app.models.user import Base
from app.core.config import settings

# Create the FastAPI app instance
app = FastAPI()

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
app.include_router(example_router, prefix=f"/api/v{api_version}", tags=["Authentication"])

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the AI Recruitment Tool API"}
