"""Document data models for processing pipeline."""
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Document processing status stages."""

    UPLOADING = "Uploading"
    PARSING = "Parsing"
    CHUNKING = "Chunking"
    GRAPH_EXTRACTING = "GraphExtracting"
    INDEXING = "Indexing"
    DONE = "Done"
    FAILED = "Failed"


class ProcessingLogEntry(BaseModel):
    """Single stage entry in document processing log."""

    stage: str = Field(..., description="Processing stage name")
    started_at: datetime = Field(..., description="Stage start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Stage completion timestamp")
    duration_ms: Optional[int] = Field(None, description="Stage duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if stage failed")

    class Config:
        json_schema_extra = {
            "example": {
                "stage": "Parsing",
                "started_at": "2026-01-27T21:00:00Z",
                "completed_at": "2026-01-27T21:00:05Z",
                "duration_ms": 5000,
                "error": None,
            }
        }


class Document(BaseModel):
    """Document metadata and processing state."""

    doc_id: str = Field(..., description="Unique document identifier (UUID format)")
    user_id: str = Field(..., description="Owner user ID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type: pdf or docx")
    file_size_bytes: int = Field(..., description="File size in bytes")
    status: ProcessingStatus = Field(..., description="Current processing status")
    current_stage: str = Field(..., description="Current processing stage name")
    error: Optional[str] = Field(None, description="Error message if processing failed")
    processing_log: List[ProcessingLogEntry] = Field(
        default_factory=list,
        description="Processing history with timestamps per stage"
    )
    page_count: Optional[int] = Field(None, description="Total pages in document")
    chunk_count: Optional[int] = Field(None, description="Total chunks created")
    entity_count: Optional[int] = Field(None, description="Total entities extracted to knowledge graph")
    relationship_count: Optional[int] = Field(None, description="Total relationships extracted to knowledge graph")
    doc_relationship_count: Optional[int] = Field(None, description="Total document-level relationships detected")
    is_demo: bool = Field(default=False, description="Whether this is a demo document visible to all users")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Document creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user123",
                "filename": "FC-001-System-Architecture.docx",
                "file_type": "docx",
                "file_size_bytes": 2048576,
                "status": "Done",
                "current_stage": "Indexing",
                "error": None,
                "processing_log": [
                    {
                        "stage": "Parsing",
                        "started_at": "2026-01-27T21:00:00Z",
                        "completed_at": "2026-01-27T21:00:05Z",
                        "duration_ms": 5000,
                        "error": None,
                    }
                ],
                "page_count": 42,
                "chunk_count": 87,
                "created_at": "2026-01-27T21:00:00Z",
                "updated_at": "2026-01-27T21:05:00Z",
            }
        }


# =============================================================================
# Docling Structured Elements
# =============================================================================

class DoclingElement(BaseModel):
    """Base class for docling document elements."""
    element_type: str = Field(..., description="Element type: text, table, section_header, list_item")
    text: str = Field(..., description="Element text content")
    page_number: Optional[int] = Field(None, description="Page number (1-indexed)")
    level: Optional[int] = Field(None, description="Hierarchy level in document tree")


class DoclingTextElement(DoclingElement):
    """Text paragraph element."""
    element_type: Literal["text"] = "text"
    label: Optional[str] = Field(None, description="Label like PARAGRAPH, CAPTION, etc.")


class DoclingTableElement(DoclingElement):
    """Table element - should never be split."""
    element_type: Literal["table"] = "table"
    num_rows: Optional[int] = Field(None, description="Number of rows")
    num_cols: Optional[int] = Field(None, description="Number of columns")
    is_atomic: bool = Field(True, description="Tables are atomic, never split")


class DoclingHeadingElement(DoclingElement):
    """Section header element."""
    element_type: Literal["section_header"] = "section_header"
    heading_level: int = Field(1, description="Heading level 1-6")


class DoclingListItemElement(DoclingElement):
    """List item element."""
    element_type: Literal["list_item"] = "list_item"
    marker: Optional[str] = Field(None, description="List marker (bullet, number)")


# Union type for all element types
DoclingElementUnion = Union[DoclingTextElement, DoclingTableElement, DoclingHeadingElement, DoclingListItemElement]


class DoclingParseResult(BaseModel):
    """Result from docling parsing with both structured and markdown output."""
    elements: List[DoclingElementUnion] = Field(default_factory=list, description="Structured elements in reading order")
    md_content: str = Field("", description="Full markdown content for fallback")
    page_count: int = Field(0, description="Total pages in document")
    raw_json: Optional[dict] = Field(None, description="Raw JSON response for debugging")


# =============================================================================
# Chunk Models
# =============================================================================

class ChunkMetadata(BaseModel):
    """Metadata for a single document chunk."""

    chunk_id: str = Field(..., description="Unique chunk identifier (doc_id-chunk-NNN format)")
    doc_id: str = Field(..., description="Parent document ID")
    user_id: str = Field(..., description="Owner user ID")
    filename: str = Field(..., description="Source document filename")
    section_title: Optional[str] = Field(None, description="Section heading")
    page_range: Optional[str] = Field(None, description="Page range (e.g., '5-7')")
    chunk_index: int = Field(..., description="Zero-based chunk position in document")
    token_count: int = Field(..., description="Approximate token count")
    text: str = Field(..., description="Chunk text content")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Chunk creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000-chunk-042",
                "doc_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user123",
                "filename": "FC-001-System-Architecture.docx",
                "section_title": "3.2 Network Configuration",
                "page_range": "12-14",
                "chunk_index": 42,
                "token_count": 1024,
                "created_at": "2026-01-27T21:05:00Z",
            }
        }
