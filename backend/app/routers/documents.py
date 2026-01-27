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

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"]
)

# File validation constants
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"
}
MAX_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024


async def validate_file(file: UploadFile) -> tuple[str, int, bytes]:
    """Validate file type and size. Returns (file_type, size, content) or raises HTTPException."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PDF, DOCX"
        )

    # Read chunks to check size without loading entire file
    size = 0
    chunks = []
    async for chunk in file.stream():
        size += len(chunk)
        if size > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
            )
        chunks.append(chunk)

    # Combine chunks
    content = b''.join(chunks)
    file_type = ALLOWED_TYPES[file.content_type]

    logger.info("file_validated",
                filename=file.filename,
                file_type=file_type,
                size_bytes=size)

    return file_type, size, content


async def process_document_background(doc_id: str, user_id: str, file_path: Path):
    """
    Background task to parse document via docling.

    NOTE: This is a placeholder implementation that only handles parsing.
    Plan 02-04 will REPLACE this function with DocumentPipeline.process_document()
    which handles the full pipeline: parse -> chunk -> index.
    """
    db = DocumentDatabase(settings.database_path)
    docling = DoclingClient()

    try:
        # Get document record
        doc = await db.get_document(doc_id)
        if not doc:
            logger.error("document_not_found_for_processing", doc_id=doc_id)
            return

        # Update to PARSING
        doc.status = ProcessingStatus.PARSING
        doc.current_stage = "Parsing"
        doc.processing_log.append(ProcessingLogEntry(
            stage="Parsing",
            started_at=datetime.utcnow()
        ))
        await db.update_document(doc)

        logger.info("doc_ingestion_started", doc_id=doc_id, user_id=user_id)

        # Parse via docling
        parse_result = await docling.parse_document(file_path)

        # Store parsed result
        storage = StorageService(settings.DATA_DIR)
        await storage.save_processed_json(user_id, doc_id, parse_result)

        # Update processing log
        doc.processing_log[-1].completed_at = datetime.utcnow()
        doc.processing_log[-1].duration_ms = int(
            (doc.processing_log[-1].completed_at - doc.processing_log[-1].started_at).total_seconds() * 1000
        )

        # Update status for next phase (chunking happens in 02-03)
        doc.status = ProcessingStatus.CHUNKING
        doc.current_stage = "Chunking"
        doc.page_count = parse_result.get("page_count")
        doc.processing_log.append(ProcessingLogEntry(
            stage="Chunking",
            started_at=datetime.utcnow()
        ))
        await db.update_document(doc)

        logger.info("doc_parsing_completed",
                   doc_id=doc_id,
                   page_count=doc.page_count)

    except DoclingError as e:
        logger.error("doc_ingestion_failed", doc_id=doc_id, error=str(e))
        doc = await db.get_document(doc_id)
        if doc:
            doc.status = ProcessingStatus.FAILED
            doc.error = str(e)
            await db.update_document(doc)
    except Exception as e:
        logger.error("doc_ingestion_unexpected_error", doc_id=doc_id, error=str(e), exc_info=True)
        doc = await db.get_document(doc_id)
        if doc:
            doc.status = ProcessingStatus.FAILED
            doc.error = f"Unexpected error: {str(e)}"
            await db.update_document(doc)


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
