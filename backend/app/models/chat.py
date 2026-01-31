"""Chat data models for RAG pipeline."""
from typing import List, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation linking answer to source document chunk."""

    id: int = Field(..., description="Footnote number [1], [2], etc.")
    doc_id: str = Field(..., description="Document UUID")
    filename: str = Field(..., description="Original filename")
    page_range: Optional[str] = Field(None, description="Page range (e.g., '42-43')")
    section_title: Optional[str] = Field(None, description="Section heading if available")
    snippet: str = Field(..., description="First 200 chars of chunk text")
    score: Optional[float] = Field(None, description="Reranker score for diagnostics")
    source: str = Field(default="document", description="Source type: 'document' or 'graph'")

    # Multi-source synthesis fields (Phase 5)
    multi_source: bool = Field(
        default=False,
        description="True if part of multi-source claim with adjacent citations"
    )
    related_doc_ids: Optional[List[str]] = Field(
        None,
        description="Related document IDs if document relationships exist"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "doc_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "FC-001-System-Architecture.docx",
                "page_range": "12-14",
                "section_title": "3.2 Network Configuration",
                "snippet": "The network architecture consists of three primary layers: edge, core, and management...",
                "score": 0.87,
                "multi_source": False,
                "related_doc_ids": None,
            }
        }


class ChatRequest(BaseModel):
    """User question request for RAG pipeline."""

    question: str = Field(..., min_length=1, max_length=2000, description="User's question")
    user_id: str = Field(..., description="User ID for document filtering")
    history: Optional[List[dict]] = Field(default=None, description="Conversation history")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the primary network layers in the system architecture?",
                "user_id": "user123",
                "history": [
                    {"role": "user", "content": "Tell me about the system."},
                    {"role": "assistant", "content": "The system consists of..."},
                ],
            }
        }


class DiagnosticInfo(BaseModel):
    """Performance diagnostics for RAG pipeline observability."""

    retrieval_count: int = Field(..., description="Number of chunks retrieved")
    rerank_count: int = Field(..., description="Number of chunks reranked")
    context_count: int = Field(..., description="Number of chunks sent to LLM")
    retrieval_latency_ms: int = Field(..., description="Retrieval duration in milliseconds")
    rerank_latency_ms: int = Field(..., description="Reranking duration in milliseconds")
    generation_latency_ms: int = Field(..., description="LLM generation duration in milliseconds")
    total_latency_ms: int = Field(..., description="Total request duration in milliseconds")
    cache_hit: bool = Field(default=False, description="Whether response was cached")

    class Config:
        json_schema_extra = {
            "example": {
                "retrieval_count": 25,
                "rerank_count": 12,
                "context_count": 10,
                "retrieval_latency_ms": 45,
                "rerank_latency_ms": 120,
                "generation_latency_ms": 850,
                "total_latency_ms": 1015,
                "cache_hit": False,
            }
        }


class ChatResponse(BaseModel):
    """RAG pipeline response with answer and citations."""

    answer: str = Field(..., description="Generated answer text")
    citations: List[Citation] = Field(default_factory=list, description="Source citations")
    request_id: str = Field(..., description="Unique request identifier for tracing")
    diagnostics: Optional[DiagnosticInfo] = Field(None, description="Performance metrics (debug mode only)")

    # Multi-source synthesis metadata (Phase 5)
    synthesis_mode: bool = Field(default=False, description="True if multi-document synthesis was used")
    source_doc_count: int = Field(default=1, description="Number of distinct source documents")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The system architecture consists of three primary network layers [1]: edge, core, and management...",
                "citations": [
                    {
                        "id": 1,
                        "doc_id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "FC-001-System-Architecture.docx",
                        "page_range": "12-14",
                        "section_title": "3.2 Network Configuration",
                        "snippet": "The network architecture consists of three primary layers...",
                        "score": 0.87,
                    }
                ],
                "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "synthesis_mode": False,
                "source_doc_count": 1,
                "diagnostics": {
                    "retrieval_count": 25,
                    "rerank_count": 12,
                    "context_count": 10,
                    "retrieval_latency_ms": 45,
                    "rerank_latency_ms": 120,
                    "generation_latency_ms": 850,
                    "total_latency_ms": 1015,
                    "cache_hit": False,
                },
            }
        }
