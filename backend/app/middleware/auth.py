"""JWT authentication middleware for FastAPI."""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError
import structlog

from app.config import settings

security = HTTPBearer()
logger = structlog.get_logger()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """
    Validate JWT token and extract user_id.

    Better Auth stores user ID in the 'sub' claim.
    Raises HTTP 401 if token is invalid or missing.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Better Auth uses 'sub' claim for user ID
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("jwt_missing_sub", payload_keys=list(payload.keys()))
            raise credentials_exception

        # Bind user_id to structlog context for this request
        structlog.contextvars.bind_contextvars(user_id=user_id)
        logger.info("user_authenticated", user_id=user_id)

        return user_id

    except InvalidTokenError as e:
        logger.warning("jwt_validation_failed", error=str(e))
        raise credentials_exception


# Optional: Dependency that makes auth optional (returns None if no token)
async def get_optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))]
) -> str | None:
    """
    Optional authentication - returns user_id if valid token provided, None otherwise.
    """
    if credentials is None:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id:
            structlog.contextvars.bind_contextvars(user_id=user_id)
        return user_id
    except InvalidTokenError:
        return None
