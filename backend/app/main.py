"""IRONMIND API - FastAPI application."""
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.database import DocumentDatabase
from app.routers import health, protected, documents

# Initialize FastAPI app
app = FastAPI(
    title="IRONMIND API",
    version="0.1.0",
    description="RAG-powered technical documentation assistant"
)

# Configure structured logging
configure_logging(settings.ENVIRONMENT)
logger = get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests and responses."""

    async def dispatch(self, request: Request, call_next):
        """Log request entry and exit with duration."""
        request_logger = get_logger()
        start_time = time.time()

        request_logger.info(
            "request_started",
            path=request.url.path,
            method=request.method
        )

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        request_logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2)
        )

        return response


# Configure CORS (must be first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
    generator=lambda: str(uuid.uuid4())
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(protected.router)
app.include_router(documents.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    db = DocumentDatabase(settings.database_path)
    await db.initialize()
    logger.info("app_startup_complete")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "IRONMIND API",
        "status": "running"
    }
