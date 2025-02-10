from fastapi import APIRouter

health_router = APIRouter()

@health_router.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "OK"}