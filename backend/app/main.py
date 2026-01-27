"""IRONMIND API - FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Initialize FastAPI app
app = FastAPI(
    title="IRONMIND API",
    version="0.1.0",
    description="RAG-powered technical documentation assistant"
)

# Configure CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Configure structured logging (Task 2)
# TODO: Add correlation ID middleware (Task 2)
# TODO: Add request logging middleware (Task 2)

# TODO: Include health router (Task 3)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "IRONMIND API",
        "status": "running"
    }
