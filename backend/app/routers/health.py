"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """
    Liveness probe - basic app health.

    Returns:
        dict: Status indicator showing service is running
    """
    return {"status": "healthy"}
