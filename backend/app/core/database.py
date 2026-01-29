"""SQLite database manager for document tracking."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import aiosqlite
import structlog

from app.models.documents import Document, ProcessingStatus, ProcessingLogEntry

logger = structlog.get_logger(__name__)


class DocumentDatabase:
    """Async SQLite database for document metadata and status tracking."""

    def __init__(self, db_path: str):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_dir()

    def _ensure_db_dir(self) -> None:
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database schema with WAL mode for concurrency."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")

            # Create documents table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    error TEXT,
                    processing_log TEXT NOT NULL,
                    page_count INTEGER,
                    chunk_count INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indexes for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_user_id
                ON documents(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_status
                ON documents(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_user_status
                ON documents(user_id, status)
            """)

            await db.commit()

        logger.info("database_initialized", db_path=self.db_path)

    async def create_document(self, doc: Document) -> None:
        """Create a new document record.

        Args:
            doc: Document model to insert
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO documents (
                    doc_id, user_id, filename, file_type, file_size_bytes,
                    status, current_stage, error, processing_log,
                    page_count, chunk_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.doc_id,
                doc.user_id,
                doc.filename,
                doc.file_type,
                doc.file_size_bytes,
                doc.status.value,
                doc.current_stage,
                doc.error,
                json.dumps([entry.model_dump(mode='json') for entry in doc.processing_log]),
                doc.page_count,
                doc.chunk_count,
                doc.created_at.isoformat(),
                doc.updated_at.isoformat(),
            ))
            await db.commit()

        logger.info(
            "document_created",
            doc_id=doc.doc_id,
            user_id=doc.user_id,
            filename=doc.filename,
        )

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document model or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM documents WHERE doc_id = ?",
                (doc_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_document(row)

    async def update_document(self, doc: Document) -> None:
        """Update existing document record.

        Args:
            doc: Document model with updated data
        """
        doc.updated_at = datetime.utcnow()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE documents SET
                    user_id = ?,
                    filename = ?,
                    file_type = ?,
                    file_size_bytes = ?,
                    status = ?,
                    current_stage = ?,
                    error = ?,
                    processing_log = ?,
                    page_count = ?,
                    chunk_count = ?,
                    updated_at = ?
                WHERE doc_id = ?
            """, (
                doc.user_id,
                doc.filename,
                doc.file_type,
                doc.file_size_bytes,
                doc.status.value,
                doc.current_stage,
                doc.error,
                json.dumps([entry.model_dump(mode='json') for entry in doc.processing_log]),
                doc.page_count,
                doc.chunk_count,
                doc.updated_at.isoformat(),
                doc.doc_id,
            ))
            await db.commit()

        logger.info(
            "document_updated",
            doc_id=doc.doc_id,
            status=doc.status.value,
            current_stage=doc.current_stage,
        )

    async def list_documents_by_user(
        self,
        user_id: str,
        status: Optional[ProcessingStatus] = None
    ) -> List[Document]:
        """List documents for a specific user.

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of Document models
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if status:
                query = """
                    SELECT * FROM documents
                    WHERE user_id = ? AND status = ?
                    ORDER BY created_at DESC
                """
                params = (user_id, status.value)
            else:
                query = """
                    SELECT * FROM documents
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """
                params = (user_id,)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        return [self._row_to_document(row) for row in rows]

    async def list_user_documents(
        self,
        user_id: str,
        status: Optional[ProcessingStatus] = None
    ) -> List[Document]:
        """Alias for list_documents_by_user for consistency.

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of Document models
        """
        return await self.list_documents_by_user(user_id, status)

    async def delete_document(self, doc_id: str) -> bool:
        """Delete document record.

        Args:
            doc_id: Document identifier

        Returns:
            True if document was deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM documents WHERE doc_id = ?",
                (doc_id,)
            )
            await db.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info("document_deleted", doc_id=doc_id)
        else:
            logger.warning("document_not_found", doc_id=doc_id)

        return deleted

    def _row_to_document(self, row: aiosqlite.Row) -> Document:
        """Convert database row to Document model.

        Args:
            row: SQLite row object

        Returns:
            Document model
        """
        # Parse processing log JSON
        processing_log_data = json.loads(row["processing_log"])
        processing_log = [
            ProcessingLogEntry(**entry) for entry in processing_log_data
        ]

        return Document(
            doc_id=row["doc_id"],
            user_id=row["user_id"],
            filename=row["filename"],
            file_type=row["file_type"],
            file_size_bytes=row["file_size_bytes"],
            status=ProcessingStatus(row["status"]),
            current_stage=row["current_stage"],
            error=row["error"],
            processing_log=processing_log,
            page_count=row["page_count"],
            chunk_count=row["chunk_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
