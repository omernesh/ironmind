"""Hybrid chunking service using chonkie library for semantic and token-based chunking."""
import tiktoken
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union, Literal
from datetime import datetime, timezone
from functools import lru_cache
from chonkie import TokenChunker as ChonkieTokenChunker
from chonkie import SemanticChunker as ChonkieSemanticChunker
from chonkie.types import Chunk as ChonkieChunk

from app.core.logging import get_logger
from app.models.documents import ChunkMetadata, DoclingParseResult
from app.config import settings

logger = get_logger()


@dataclass
class ChunkingResult:
    """Result of chunking operation with metadata about mode used."""
    chunks: List[ChunkMetadata]
    mode_used: str  # "semantic", "token", "token_fallback"
    fallback_reason: Optional[str] = None
    total_tokens: int = 0
    avg_tokens: float = 0.0


class SemanticChunker:
    """
    Hybrid chunker using chonkie library for production-grade chunking.
    Supports both token-based and semantic chunking strategies.

    Key features:
    - Semantic chunking for coherent, meaningful chunk boundaries
    - Token-based chunking for speed and simplicity
    - Configurable chunking mode (semantic/token/auto)
    - Hard max_tokens enforcement for safety
    - Singleton pattern for efficient model reuse
    - Async support for non-blocking operation
    """

    def __init__(
        self,
        target_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        overlap_pct: Optional[float] = None,
        min_chunk_tokens: Optional[int] = None,
        mode: Optional[Literal["semantic", "token", "auto"]] = None,
        embedding_model: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        model_cache_dir: Optional[str] = None
    ):
        """
        Initialize the hybrid chunker with configurable strategy.

        All parameters default to settings from app.config if not provided.

        Args:
            target_tokens: Target chunk size in tokens
            max_tokens: Hard maximum tokens per chunk
            overlap_pct: Percentage of overlap between chunks for token mode
            min_chunk_tokens: Minimum chunk size
            mode: Chunking strategy - "semantic", "token", or "auto"
            embedding_model: Embedding model for semantic chunking
            similarity_threshold: Similarity threshold for semantic splitting
            model_cache_dir: Directory to cache downloaded models
        """
        # Use settings as defaults
        self.target_tokens = target_tokens or settings.CHUNKING_TARGET_TOKENS
        self.max_tokens = max_tokens or settings.CHUNKING_MAX_TOKENS
        self.overlap_pct = overlap_pct or settings.CHUNKING_OVERLAP_PCT
        self.min_chunk_tokens = min_chunk_tokens or settings.CHUNKING_MIN_CHUNK_TOKENS
        self.mode = mode or settings.CHUNKING_MODE
        self.embedding_model = embedding_model or settings.CHUNKING_EMBEDDING_MODEL
        self.similarity_threshold = similarity_threshold or settings.CHUNKING_SIMILARITY_THRESHOLD
        self.model_cache_dir = model_cache_dir or settings.CHUNKING_MODEL_CACHE_DIR

        # Initialize tiktoken encoder for token counting
        self.encoder = tiktoken.get_encoding("cl100k_base")

        # Initialize chunkers based on mode
        overlap_tokens = int(self.target_tokens * self.overlap_pct)

        if self.mode in ["semantic", "auto"]:
            # Initialize semantic chunker with embedding model
            try:
                logger.info("initializing_semantic_chunker",
                           embedding_model=self.embedding_model,
                           target_tokens=self.target_tokens,
                           threshold=self.similarity_threshold,
                           cache_dir=self.model_cache_dir)

                self.semantic_chunker = ChonkieSemanticChunker(
                    embedding_model=self.embedding_model,
                    chunk_size=self.target_tokens,
                    threshold=self.similarity_threshold,
                    similarity_window=3,
                    min_sentences_per_chunk=1,
                    min_characters_per_sentence=24
                )
                logger.info("semantic_chunker_initialized_successfully")
            except Exception as e:
                logger.error("semantic_chunker_initialization_failed",
                            error=str(e),
                            error_type=type(e).__name__)
                if self.mode == "semantic":
                    # In semantic mode, failure is critical
                    raise RuntimeError(
                        f"Failed to initialize semantic chunker: {e}. "
                        "Check network connectivity and embedding model availability."
                    ) from e
                else:
                    # In auto mode, fall back gracefully
                    logger.warning("falling_back_to_token_chunker_due_to_semantic_init_failure")
                    self.mode = "token"

        if self.mode in ["token", "auto"] or not hasattr(self, 'semantic_chunker'):
            # Initialize token chunker as fallback or primary
            self.token_chunker = ChonkieTokenChunker(
                tokenizer="cl100k_base",
                chunk_size=self.target_tokens,
                chunk_overlap=overlap_tokens
            )
            logger.info("token_chunker_initialized",
                       target_tokens=self.target_tokens,
                       overlap_tokens=overlap_tokens)

        logger.info("chunker_initialized",
                   mode=self.mode,
                   target_tokens=self.target_tokens,
                   max_tokens=self.max_tokens,
                   library="chonkie",
                   config_source="settings")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoder.encode(text))

    def chunk_document(
        self,
        docling_output: Union[Dict[str, Any], DoclingParseResult],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[ChunkMetadata]:
        """
        Main chunking method - maintains existing interface for pipeline compatibility.

        Returns List[ChunkMetadata] for backward compatibility.
        Use chunk_document_with_metadata() for detailed results including mode used.

        Args:
            docling_output: Either DoclingParseResult or dict with md_content/json_content
            doc_id: Document ID
            user_id: User ID
            filename: Original filename

        Returns:
            List of ChunkMetadata objects
        """
        result = self.chunk_document_with_metadata(docling_output, doc_id, user_id, filename)

        # Log mode used for visibility
        if result.fallback_reason:
            logger.warning("chunking_used_fallback",
                          doc_id=doc_id,
                          requested_mode=self.mode,
                          actual_mode=result.mode_used,
                          reason=result.fallback_reason)

        return result.chunks

    def chunk_document_with_metadata(
        self,
        docling_output: Union[Dict[str, Any], DoclingParseResult],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> ChunkingResult:
        """
        Chunking method with detailed result metadata.

        Strategy (Hybrid Approach):
        1. Extract text from docling_output (markdown or json_content)
        2. Choose chunking strategy based on mode and document size
        3. Use semantic chunking for coherent boundaries OR token chunking for speed
        4. Enforce max_tokens hard limit (safety fallback)
        5. Return detailed result with mode used

        Args:
            docling_output: Either DoclingParseResult or dict with md_content/json_content
            doc_id: Document ID
            user_id: User ID
            filename: Original filename

        Returns:
            ChunkingResult with chunks and metadata
        """
        # Extract text content
        text = self._extract_text(docling_output)

        if not text or not text.strip():
            logger.warning("empty_document_skipping_chunking", doc_id=doc_id)
            return ChunkingResult(chunks=[], mode_used="none", total_tokens=0, avg_tokens=0.0)

        text_tokens = self.count_tokens(text)
        logger.info("chunking_document",
                   doc_id=doc_id,
                   text_length=len(text),
                   text_tokens=text_tokens,
                   requested_mode=self.mode)

        # Determine which chunker to use
        use_semantic = self._should_use_semantic(text_tokens)
        fallback_reason = None

        # Chunk using selected strategy
        try:
            if use_semantic and hasattr(self, 'semantic_chunker'):
                logger.info("using_semantic_chunking", doc_id=doc_id, text_tokens=text_tokens)
                chonkie_chunks = self.semantic_chunker(text)
                chunking_mode = "semantic"
            else:
                logger.info("using_token_chunking", doc_id=doc_id, text_tokens=text_tokens)
                chonkie_chunks = self.token_chunker(text)
                chunking_mode = "token"

            logger.info("chonkie_chunking_completed",
                       doc_id=doc_id,
                       mode=chunking_mode,
                       num_chunks=len(chonkie_chunks))
        except Exception as e:
            logger.error("chonkie_chunking_failed",
                        doc_id=doc_id,
                        error=str(e),
                        error_type=type(e).__name__)
            # Fallback to token chunker if semantic fails
            if use_semantic and hasattr(self, 'token_chunker'):
                logger.warning("falling_back_to_token_chunker_after_error", doc_id=doc_id)
                chonkie_chunks = self.token_chunker(text)
                chunking_mode = "token_fallback"
                fallback_reason = f"Semantic chunking failed: {type(e).__name__}"
            else:
                raise

        # Convert to ChunkMetadata and enforce limits
        chunk_metadatas = []
        oversized_count = 0

        for idx, chunk in enumerate(chonkie_chunks):
            # Enforce hard max_tokens limit
            if chunk.token_count > self.max_tokens:
                logger.warning("oversized_chunk_detected",
                              doc_id=doc_id,
                              chunk_index=idx,
                              token_count=chunk.token_count,
                              max_tokens=self.max_tokens)
                oversized_count += 1

                # Split oversized chunks using emergency fallback
                split_chunks = self._emergency_split(chunk, doc_id, user_id, filename, idx)
                chunk_metadatas.extend(split_chunks)
            else:
                chunk_metadata = self._create_chunk_metadata(
                    chunk, doc_id, user_id, filename, idx
                )
                chunk_metadatas.append(chunk_metadata)

        # Validate all chunks before returning
        for chunk in chunk_metadatas:
            assert chunk.token_count <= self.max_tokens, \
                f"Critical: chunk {chunk.chunk_id} exceeds max ({chunk.token_count} > {self.max_tokens})"

        # Log statistics
        self._log_statistics(chunk_metadatas, doc_id, oversized_count, chunking_mode)

        # Calculate stats
        token_counts = [c.token_count for c in chunk_metadatas]
        total_tokens = sum(token_counts)
        avg_tokens = total_tokens / len(token_counts) if token_counts else 0.0

        return ChunkingResult(
            chunks=chunk_metadatas,
            mode_used=chunking_mode,
            fallback_reason=fallback_reason,
            total_tokens=total_tokens,
            avg_tokens=avg_tokens
        )

    async def chunk_document_async(
        self,
        docling_output: Union[Dict[str, Any], DoclingParseResult],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> ChunkingResult:
        """
        Async wrapper for chunk_document_with_metadata.

        Runs CPU-intensive chunking in thread pool to avoid blocking event loop.

        Args:
            docling_output: Either DoclingParseResult or dict with md_content/json_content
            doc_id: Document ID
            user_id: User ID
            filename: Original filename

        Returns:
            ChunkingResult with chunks and metadata
        """
        return await asyncio.to_thread(
            self.chunk_document_with_metadata,
            docling_output,
            doc_id,
            user_id,
            filename
        )

    def _should_use_semantic(self, text_tokens: int) -> bool:
        """
        Determine whether to use semantic or token chunking.

        Args:
            text_tokens: Number of tokens in the document

        Returns:
            True if semantic chunking should be used, False for token chunking
        """
        if self.mode == "semantic":
            return True
        elif self.mode == "token":
            return False
        elif self.mode == "auto":
            # Use semantic for larger documents (better coherence)
            # Use token for small documents (faster, simpler)
            # Threshold: 5000 tokens (~5 pages of text)
            threshold = 5000
            use_semantic = text_tokens >= threshold
            logger.debug("auto_mode_decision",
                        text_tokens=text_tokens,
                        threshold=threshold,
                        use_semantic=use_semantic)
            return use_semantic
        else:
            return True  # Default to semantic

    def _extract_text(self, docling_output: Union[Dict[str, Any], DoclingParseResult]) -> str:
        """
        Extract text content from docling output.

        Tries md_content first (markdown), falls back to json_content if it's a dict.

        Args:
            docling_output: Docling parser output

        Returns:
            Extracted text content
        """
        if isinstance(docling_output, dict):
            # Handle both nested {"document": {"md_content": ...}} and flat {"md_content": ...}
            if "document" in docling_output:
                text = docling_output.get("document", {}).get("md_content", "")
            else:
                text = docling_output.get("md_content") or docling_output.get("json_content", "")
        else:
            # DoclingParseResult object
            text = docling_output.md_content or ""

        return text

    def _create_chunk_metadata(
        self,
        chunk: ChonkieChunk,
        doc_id: str,
        user_id: str,
        filename: str,
        chunk_index: int
    ) -> ChunkMetadata:
        """
        Convert chonkie Chunk to ChunkMetadata.

        Args:
            chunk: Chonkie chunk object
            doc_id: Document ID
            user_id: User ID
            filename: Original filename
            chunk_index: Sequential chunk index

        Returns:
            ChunkMetadata object
        """
        return ChunkMetadata(
            chunk_id=f"{doc_id}-chunk-{chunk_index:03d}",
            doc_id=doc_id,
            user_id=user_id,
            filename=filename,
            section_title=None,  # Could extract from text in future enhancement
            page_range=None,     # Could extract from docling metadata in future
            chunk_index=chunk_index,
            token_count=chunk.token_count,
            text=chunk.text,
            created_at=datetime.now(timezone.utc)
        )

    def _emergency_split(
        self,
        chunk: ChonkieChunk,
        doc_id: str,
        user_id: str,
        filename: str,
        base_index: int
    ) -> List[ChunkMetadata]:
        """
        Emergency split for chunks exceeding max_tokens.

        Uses optimized character-based estimation then exact token verification.

        Args:
            chunk: Oversized chonkie chunk
            doc_id: Document ID
            user_id: User ID
            filename: Original filename
            base_index: Base chunk index for numbering

        Returns:
            List of split ChunkMetadata objects
        """
        chunks = []
        # Approximate: 1 token ≈ 4 chars for English text
        approx_chars_per_token = 4
        target_chars = self.max_tokens * approx_chars_per_token

        words = chunk.text.split()
        current_words = []
        current_char_count = 0
        sub_index = 0

        for word in words:
            word_len = len(word) + 1  # +1 for space

            # Use character count for fast approximation
            if current_char_count + word_len <= target_chars:
                current_words.append(word)
                current_char_count += word_len
            else:
                # Flush current chunk with exact token verification
                if current_words:
                    text = " ".join(current_words)
                    token_count = self.count_tokens(text)

                    # Double-check token limit
                    if token_count > self.max_tokens:
                        # Rare case: remove words until under limit
                        while current_words and token_count > self.max_tokens:
                            current_words.pop()
                            text = " ".join(current_words)
                            token_count = self.count_tokens(text)

                    if current_words:  # May be empty after adjustment
                        chunks.append(ChunkMetadata(
                            chunk_id=f"{doc_id}-chunk-{base_index:03d}-{sub_index}",
                            doc_id=doc_id,
                            user_id=user_id,
                            filename=filename,
                            section_title=None,
                            page_range=None,
                            chunk_index=base_index * 1000 + sub_index,
                            token_count=token_count,
                            text=text,
                            created_at=datetime.now(timezone.utc)
                        ))
                        sub_index += 1

                # Start new chunk
                current_words = [word]
                current_char_count = word_len

        # Flush final chunk
        if current_words:
            text = " ".join(current_words)
            token_count = self.count_tokens(text)

            # Final verification
            assert token_count <= self.max_tokens, \
                f"Emergency split failed: {token_count} > {self.max_tokens}"

            chunks.append(ChunkMetadata(
                chunk_id=f"{doc_id}-chunk-{base_index:03d}-{sub_index}",
                doc_id=doc_id,
                user_id=user_id,
                filename=filename,
                section_title=None,
                page_range=None,
                chunk_index=base_index * 1000 + sub_index,
                token_count=token_count,
                text=text,
                created_at=datetime.now(timezone.utc)
            ))

        logger.info("emergency_split_completed",
                   doc_id=doc_id,
                   base_index=base_index,
                   original_tokens=chunk.token_count,
                   split_chunks=len(chunks))

        return chunks

    def _log_statistics(
        self,
        chunks: List[ChunkMetadata],
        doc_id: str,
        oversized_count: int,
        chunking_mode: str = "unknown"
    ):
        """
        Log chunking statistics for monitoring.

        Args:
            chunks: List of chunk metadata objects
            doc_id: Document ID
            oversized_count: Number of chunks that exceeded max_tokens
            chunking_mode: Which chunking mode was used (semantic/token/token_fallback)
        """
        if not chunks:
            logger.warning("no_chunks_produced", doc_id=doc_id)
            return

        token_counts = [c.token_count for c in chunks]

        stats = {
            "doc_id": doc_id,
            "chunking_mode": chunking_mode,
            "total_chunks": len(chunks),
            "oversized_chunks": oversized_count,
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "avg_tokens": sum(token_counts) / len(token_counts),
            "total_tokens": sum(token_counts)
        }

        logger.info("chunking_statistics", **stats)

        # Validate max token constraint
        max_chunk_tokens = max(token_counts)
        if max_chunk_tokens > self.max_tokens:
            logger.error("max_token_violation",
                        doc_id=doc_id,
                        max_chunk_tokens=max_chunk_tokens,
                        limit=self.max_tokens)
            raise ValueError(
                f"Chunk exceeds max_tokens limit: {max_chunk_tokens} > {self.max_tokens}"
            )


# Singleton pattern for efficient model reuse
@lru_cache(maxsize=1)
def get_chunker() -> SemanticChunker:
    """
    Get singleton chunker instance.

    Uses LRU cache to ensure only one instance is created.
    All settings are loaded from app.config.

    Returns:
        Shared SemanticChunker instance
    """
    logger.info("creating_singleton_chunker_instance")
    return SemanticChunker()
