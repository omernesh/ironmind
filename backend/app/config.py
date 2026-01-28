"""Application configuration using pydantic-settings."""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "ironmind-backend"
    LOG_LEVEL: str = "INFO"

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Document Processing
    DATA_DIR: str = "/app/data"
    DOCLING_URL: str = "http://docling:5001"
    MAX_FILE_SIZE_MB: int = 10
    MAX_DOCUMENTS_PER_USER: int = 10

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def database_path(self) -> str:
        """Get database file path."""
        return f"{self.DATA_DIR}/documents.db"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars without validation errors


# Singleton settings instance
settings = Settings()
