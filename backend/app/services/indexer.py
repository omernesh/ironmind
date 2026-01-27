"""txtai-based indexer service for document chunks."""
from pathlib import Path
from typing import List, Optional, Dict, Any
from txtai.embeddings import Embeddings
from app.core.logging import get_logger
from app.models.documents import ChunkMetadata
from app.config import settings

logger = get_logger()


class TxtaiIndexer:
    """
    Txtai-based indexer for document chunks.

    Uses content storage to persist full text and metadata
    alongside vector embeddings for retrieval.
    """

    def __init__(self, index_path: Optional[str] = None):
        self.index_path = Path(index_path or f"{settings.DATA_DIR}/index")
        self.index_path.mkdir(parents=True, exist_ok=True)

        self.embeddings = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """Initialize txtai embeddings with content storage."""
        config = {
            # Use OpenAI embeddings (configured via env var OPENAI_API_KEY)
            "path": "sentence-transformers/all-MiniLM-L6-v2",  # Fallback for POC
            "content": True,  # Enable metadata storage - CRITICAL
            "backend": "sqlite",
            "functions": [
                {"name": "user_filter", "function": "app.services.indexer.user_filter"}
            ]
        }

        self.embeddings = Embeddings(config)

        # Load existing index if present
        if (self.index_path / "embeddings").exists():
            self.embeddings.load(str(self.index_path))
            logger.info("index_loaded", path=str(self.index_path))

    def index_chunks(self, chunks: List[ChunkMetadata], user_id: str, doc_id: str) -> int:
        """
        Index chunks for a document.

        Args:
            chunks: List of ChunkMetadata to index
            user_id: User ID for filtering
            doc_id: Document ID

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            logger.warning("no_chunks_to_index", doc_id=doc_id)
            return 0

        # Convert to txtai format: (id, document_dict, tags)
        documents = []
        for chunk in chunks:
            doc = {
                "id": chunk.chunk_id,
                "text": chunk.text,
                "doc_id": chunk.doc_id,
                "user_id": chunk.user_id,
                "filename": chunk.filename,
                "section_title": chunk.section_title,
                "page_range": chunk.page_range,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "created_at": chunk.created_at.isoformat()
            }
            documents.append((chunk.chunk_id, doc, None))

        # Index documents
        self.embeddings.index(documents)

        # Save index
        self.embeddings.save(str(self.index_path))

        logger.info("chunks_indexed",
                   doc_id=doc_id,
                   user_id=user_id,
                   count=len(chunks))

        return len(chunks)

    def delete_document_chunks(self, doc_id: str) -> int:
        """Delete all chunks for a document."""
        # Query for all chunks with this doc_id
        try:
            results = self.embeddings.search(
                f"SELECT id FROM txtai WHERE doc_id = '{doc_id}'",
                limit=10000
            )

            if results:
                chunk_ids = [r["id"] for r in results]
                self.embeddings.delete(chunk_ids)
                self.embeddings.save(str(self.index_path))
                logger.info("chunks_deleted", doc_id=doc_id, count=len(chunk_ids))
                return len(chunk_ids)
        except Exception as e:
            logger.warning("delete_chunks_failed", doc_id=doc_id, error=str(e))

        return 0

    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for chunks matching query, filtered by user_id.

        Args:
            query: Search query
            user_id: User ID to filter results
            limit: Maximum results

        Returns:
            List of matching chunks with scores
        """
        # Use SQL for metadata filtering
        sql = f"""
            SELECT id, text, doc_id, filename, section_title, page_range, score
            FROM txtai
            WHERE user_id = '{user_id}'
            ORDER BY score DESC
            LIMIT {limit}
        """

        results = self.embeddings.search(query, limit=limit)

        # Filter by user_id (txtai SQL filtering)
        filtered = [
            r for r in results
            if r.get("user_id") == user_id
        ]

        return filtered[:limit]

    def get_document_chunks(self, doc_id: str, user_id: str) -> List[Dict]:
        """Get all chunks for a document."""
        try:
            results = self.embeddings.search(
                f"SELECT * FROM txtai WHERE doc_id = '{doc_id}' AND user_id = '{user_id}' ORDER BY chunk_index",
                limit=10000
            )
            return results
        except Exception as e:
            logger.warning("get_chunks_failed", doc_id=doc_id, error=str(e))
            return []


def user_filter(user_id: str, doc_user_id: str) -> bool:
    """Filter function for user_id matching."""
    return user_id == doc_user_id
