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
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_FALLBACK_MODEL: str = "gpt-4o"  # Emergency fallback when gpt-4o-mini unavailable
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

    # Knowledge Graph - FalkorDB
    FALKORDB_URL: str = "redis://falkordb:6379"  # Docker service
    FALKORDB_GRAPH_NAME: str = "aerospace_kb"  # Graph database name
    GRAPH_TRAVERSAL_DEPTH: int = 2  # Max hops for queries
    ENTITY_SIMILARITY_THRESHOLD: float = 0.85  # For resolution

    # Chunking Configuration
    CHUNKING_MODE: str = "semantic"  # semantic/token/auto
    CHUNKING_TARGET_TOKENS: int = 1000  # Target chunk size
    CHUNKING_MAX_TOKENS: int = 10000  # Hard limit (safety)
    CHUNKING_OVERLAP_PCT: float = 0.15  # 15% overlap (token mode)
    CHUNKING_MIN_CHUNK_TOKENS: int = 50  # Minimum chunk size
    CHUNKING_EMBEDDING_MODEL: str = "minishlab/potion-base-32M"  # Semantic model
    CHUNKING_SIMILARITY_THRESHOLD: float = 0.5  # Semantic split threshold
    CHUNKING_MODEL_CACHE_DIR: str = "/app/models"  # Model cache location

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
