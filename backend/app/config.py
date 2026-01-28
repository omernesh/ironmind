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

    # RAG Pipeline - LLM and Embeddings
    OPENAI_API_KEY: str = ""  # Required for embeddings + LLM
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-5-mini"
    LLM_TEMPERATURE: float = 0.1  # Low for factual accuracy
    LLM_MAX_TOKENS: int = 500

    # RAG Pipeline - Reranker
    DEEPINFRA_API_KEY: str = ""  # Required for reranker
    RERANK_MODEL: str = "Qwen/Qwen3-Reranker-0.6B"  # DeepInfra model path

    # Hybrid Search Settings
    HYBRID_WEIGHT: float = 0.5  # 50/50 semantic/BM25
    RETRIEVAL_LIMIT: int = 25  # Initial retrieval count
    RERANK_LIMIT: int = 12  # Chunks to reranker
    CONTEXT_LIMIT: int = 10  # Chunks to LLM
    RELEVANCE_THRESHOLD: float = 0.3  # Minimum score to include

    # Cache Settings
    CACHE_TTL_SECONDS: int = 300  # 5 min default

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
