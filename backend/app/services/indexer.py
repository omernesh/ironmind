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
        """Initialize txtai embeddings with hybrid search and OpenAI embeddings."""
        # Use OpenAI embeddings if API key available, fallback to local model
        if settings.OPENAI_API_KEY:
            embedding_path = f"openai/{settings.OPENAI_EMBEDDING_MODEL}"
            logger.info("using_openai_embeddings", model=settings.OPENAI_EMBEDDING_MODEL)
        else:
            embedding_path = "sentence-transformers/all-MiniLM-L6-v2"
            logger.warning("openai_key_missing", fallback="sentence-transformers/all-MiniLM-L6-v2")

        config = {
            "path": embedding_path,
            "content": True,  # Store metadata - CRITICAL
            "backend": "sqlite",
            "hybrid": True,  # Enable hybrid search (semantic + BM25)
            "scoring": {
                "method": "bm25",
                "normalize": True  # REQUIRED for RRF fusion - normalizes BM25 scores to 0-1
            },
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

        # Batch documents to respect OpenAI's 300K token-per-request limit
        # Use conservative batch size of 200K tokens to account for overhead
        MAX_BATCH_TOKENS = 200_000
        batches = self._create_batches(documents, chunks, MAX_BATCH_TOKENS)

        logger.info("indexing_in_batches",
                   doc_id=doc_id,
                   total_chunks=len(chunks),
                   num_batches=len(batches))

        # Index each batch
        for batch_idx, batch in enumerate(batches):
            batch_tokens = sum(d[1].get("token_count", 0) for d in batch)
            logger.debug("indexing_batch",
                        doc_id=doc_id,
                        batch=batch_idx + 1,
                        batch_size=len(batch),
                        batch_tokens=batch_tokens)
            self.embeddings.index(batch)

        # Save index after all batches
        self.embeddings.save(str(self.index_path))

        logger.info("chunks_indexed",
                   doc_id=doc_id,
                   user_id=user_id,
                   count=len(chunks))

        return len(chunks)

    def _create_batches(
        self,
        documents: List[tuple],
        chunks: List[ChunkMetadata],
        max_batch_tokens: int
    ) -> List[List[tuple]]:
        """
        Create batches of documents that respect token limits.

        Args:
            documents: List of (id, doc_dict, tags) tuples
            chunks: Original chunks with token counts
            max_batch_tokens: Maximum tokens per batch

        Returns:
            List of batches, each batch is a list of documents
        """
        batches = []
        current_batch = []
        current_batch_tokens = 0

        for doc, chunk in zip(documents, chunks):
            doc_tokens = chunk.token_count

            # If single chunk exceeds limit, still index it (API will handle)
            if doc_tokens > max_batch_tokens:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_batch_tokens = 0
                batches.append([doc])
                logger.warning("chunk_exceeds_batch_limit",
                             chunk_id=chunk.chunk_id,
                             tokens=doc_tokens)
                continue

            # Start new batch if adding this chunk would exceed limit
            if current_batch_tokens + doc_tokens > max_batch_tokens:
                batches.append(current_batch)
                current_batch = [doc]
                current_batch_tokens = doc_tokens
            else:
                current_batch.append(doc)
                current_batch_tokens += doc_tokens

        # Add remaining batch
        if current_batch:
            batches.append(current_batch)

        return batches

    def delete_document_chunks(self, doc_id: str) -> int:
        """
        Delete all chunks for a document.

        Works with both hybrid and non-hybrid indices.
        When hybrid search is enabled, clears both semantic and BM25 indices.
        """
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

    def reindex_document(
        self,
        chunks: List[ChunkMetadata],
        user_id: str,
        doc_id: str
    ) -> int:
        """
        Re-index a document, removing old chunks first.

        Ensures INDEX-05: Re-ingesting same document updates cleanly without duplication.

        Args:
            chunks: New chunks to index
            user_id: User ID
            doc_id: Document ID

        Returns:
            Number of chunks indexed
        """
        # Delete existing chunks for this document
        deleted = self.delete_document_chunks(doc_id)
        if deleted > 0:
            logger.info("old_chunks_deleted", doc_id=doc_id, count=deleted)

        # Index new chunks
        indexed = self.index_chunks(chunks, user_id, doc_id)

        logger.info("document_reindexed",
                   doc_id=doc_id,
                   deleted=deleted,
                   indexed=indexed)

        return indexed

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

    def hybrid_search(
        self,
        query: str,
        user_id: str,
        limit: int = 25,
        weights: float = 0.5,  # 0.5 = equal semantic/BM25
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and BM25 with user filtering.

        Uses txtai's built-in hybrid search with normalized score fusion.
        Score normalization (scoring.normalize=True) enables proper fusion
        equivalent to Reciprocal Rank Fusion (RRF).

        Includes both user's own documents and demo documents (is_demo=1).

        Args:
            query: Search query
            user_id: User ID for filtering (multi-tenant isolation)
            limit: Max results to return
            weights: Semantic/BM25 balance (0=BM25 only, 1=semantic only, 0.5=equal)
            threshold: Minimum score to include (filters low-relevance results)

        Returns:
            List of chunks with scores and full metadata
        """
        if not self.embeddings:
            logger.warning("embeddings_not_initialized")
            return []

        try:
            # Get demo document IDs from database for filtering
            demo_doc_ids = self._get_demo_document_ids()

            # Execute hybrid search with weights parameter
            # txtai handles fusion internally when hybrid=True
            results = self.embeddings.search(
                query,
                limit=limit * 2,  # Fetch more for post-filtering
                weights=weights
            )

            # Filter by user_id (or demo documents) and threshold
            filtered = []
            for result in results:
                chunk_user_id = result.get("user_id")
                chunk_doc_id = result.get("doc_id")

                # Accept chunks from user's documents OR demo documents
                if chunk_user_id != user_id and chunk_doc_id not in demo_doc_ids:
                    continue

                score = result.get("score", 0)
                if score < threshold:
                    continue
                filtered.append({
                    "chunk_id": result.get("id"),
                    "text": result.get("text"),
                    "doc_id": result.get("doc_id"),
                    "filename": result.get("filename"),
                    "page_range": result.get("page_range"),
                    "section_title": result.get("section_title"),
                    "score": score,
                    "user_id": chunk_user_id  # Preserve original user_id
                })

            # Limit to requested count
            return filtered[:limit]

        except Exception as e:
            logger.error("hybrid_search_failed", error=str(e), user_id=user_id)
            return []

    def _get_demo_document_ids(self) -> set:
        """Get set of document IDs marked as demo documents.

        Returns:
            Set of doc_ids where is_demo=1
        """
        try:
            import sqlite3
            db_path = f"{settings.DATA_DIR}/documents.db"

            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT doc_id FROM documents WHERE is_demo = 1")
            demo_doc_ids = {row[0] for row in cursor.fetchall()}
            conn.close()

            logger.debug("demo_documents_loaded", count=len(demo_doc_ids))
            return demo_doc_ids
        except Exception as e:
            logger.warning("failed_to_load_demo_documents", error=str(e))
            return set()

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
