"""Protected endpoints requiring authentication."""
from typing import Annotated
from fastapi import APIRouter, Depends
import structlog

from app.middleware.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["protected"])
logger = structlog.get_logger()


@router.get("/protected")
async def protected_endpoint(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Test endpoint that requires authentication.
    Returns user_id to verify auth is working.
    """
    logger.info("protected_endpoint_accessed", user_id=user_id)
    return {
        "message": "You have accessed a protected endpoint",
        "user_id": user_id
    }


@router.get("/me")
async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Returns current user information.
    This endpoint will be expanded when we add user profile data.
    """
    return {
        "user_id": user_id,
        "authenticated": True
    }
