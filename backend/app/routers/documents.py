"""Document upload and management endpoints."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import Response
import structlog

from app.config import settings
from app.middleware.auth import get_current_user_id
from app.models.documents import Document, ProcessingStatus, ProcessingLogEntry
from app.core.database import DocumentDatabase
from app.services.storage import StorageService
from app.services.docling_client import DoclingClient, DoclingError
from app.services.pipeline import DocumentPipeline, calculate_progress, estimate_time_remaining

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"]
)

# File validation constants
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc"
}
MAX_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024


async def validate_file(file: UploadFile) -> tuple[str, int, bytes]:
    """Validate file type and size. Returns (file_type, size, content) or raises HTTPException."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PDF, DOCX, DOC"
        )

    # Read file content and check size
    content = await file.read()
    size = len(content)

    if size > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
        )
    file_type = ALLOWED_TYPES[file.content_type]

    logger.info("file_validated",
                filename=file.filename,
                file_type=file_type,
                size_bytes=size)

    return file_type, size, content


async def process_document_background(doc_id: str, user_id: str, file_path: Path):
    """
    Background task to process document through complete pipeline.

    This replaces the placeholder parsing-only implementation from Plan 02-02.
    Now uses DocumentPipeline for full flow: parse -> chunk -> index.
    """
    pipeline = DocumentPipeline()
    await pipeline.process_document(doc_id, user_id, file_path)


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload a document for processing.

    Accepts PDF or DOCX files up to 10MB.
    Maximum 10 documents per user.
    """
    # Check document count limit
    db = DocumentDatabase(settings.database_path)
    existing_docs = await db.list_documents_by_user(user_id)

    if len(existing_docs) >= settings.MAX_DOCUMENTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_DOCUMENTS_PER_USER} documents per user"
        )

    # Validate file
    file_type, file_size, content = await validate_file(file)

    # Generate document ID
    doc_id = str(uuid.uuid4())

    # Save file to storage
    storage = StorageService(settings.DATA_DIR)
    file_path = await storage.save_upload(user_id, doc_id, file.filename, content)

    # Create document record
    doc = Document(
        doc_id=doc_id,
        user_id=user_id,
        filename=file.filename,
        file_type=file_type,
        file_size_bytes=file_size,
        status=ProcessingStatus.UPLOADING,
        current_stage="Uploading",
        processing_log=[
            ProcessingLogEntry(
                stage="Uploading",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_ms=0
            )
        ]
    )

    await db.create_document(doc)

    # Add background task for processing
    background_tasks.add_task(process_document_background, doc_id, user_id, file_path)

    logger.info("document_uploaded",
                doc_id=doc_id,
                user_id=user_id,
                filename=file.filename)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "status": ProcessingStatus.UPLOADING.value
    }


@router.get("", response_model=List[Document])
async def list_documents(
    user_id: str = Depends(get_current_user_id)
):
    """List all documents for the authenticated user."""
    db = DocumentDatabase(settings.database_path)
    documents = await db.list_documents_by_user(user_id)

    logger.info("documents_listed", user_id=user_id, count=len(documents))

    return documents


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get document processing status with progress and time estimate.

    Returns status values for INGEST-10:
    - "Processing" (maps to Uploading, Parsing, Chunking, Indexing stages)
    - "Indexed" (maps to Done status)
    - "Failed" (maps to Failed status)

    Note: Frontend UI to display this status is implemented in Phase 6.
    """
    db = DocumentDatabase(settings.database_path)
    doc = await db.get_document(doc_id)

    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.user_id != user_id:
        raise HTTPException(403, "Not authorized to view this document")

    # Map internal status to INGEST-10 status values
    if doc.status == ProcessingStatus.DONE:
        display_status = "Indexed"
    elif doc.status == ProcessingStatus.FAILED:
        display_status = "Failed"
    else:
        display_status = "Processing"

    return {
        "doc_id": doc.doc_id,
        "filename": doc.filename,
        "status": display_status,  # INGEST-10 compliant: Processing, Indexed, Failed
        "internal_status": doc.status.value,  # Detailed status for debugging
        "current_stage": doc.current_stage,
        "progress_pct": calculate_progress(doc.status, doc.current_stage),
        "estimated_time_remaining": estimate_time_remaining(doc.current_stage, doc.page_count),
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "processing_log": [
            {
                "stage": entry.stage,
                "started_at": entry.started_at.isoformat(),
                "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
                "duration_ms": entry.duration_ms
            }
            for entry in doc.processing_log
        ],
        "error": doc.error if doc.status == ProcessingStatus.FAILED else None,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat()
    }


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a document and all associated files."""
    db = DocumentDatabase(settings.database_path)

    # Verify document exists and belongs to user
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if doc.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )

    # Delete from database
    await db.delete_document(doc_id)

    # Delete files
    storage = StorageService(settings.DATA_DIR)
    storage.delete_document_files(user_id, doc_id)

    logger.info("document_deleted", doc_id=doc_id, user_id=user_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
