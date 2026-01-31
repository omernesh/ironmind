"""Hybrid chunking service using chonkie library for semantic and token-based chunking."""
import tiktoken
from typing import List, Dict, Optional, Any, Union, Literal
from datetime import datetime, timezone
from chonkie import TokenChunker as ChonkieTokenChunker
from chonkie import SemanticChunker as ChonkieSemanticChunker
from chonkie.types import Chunk as ChonkieChunk

from app.core.logging import get_logger
from app.models.documents import ChunkMetadata, DoclingParseResult

logger = get_logger()


class SemanticChunker:
    """
    Hybrid chunker using chonkie library for production-grade chunking.
    Supports both token-based and semantic chunking strategies.

    Key features:
    - Semantic chunking for coherent, meaningful chunk boundaries
    - Token-based chunking for speed and simplicity
    - Configurable chunking mode (semantic/token/auto)
    - Hard max_tokens enforcement for safety
    - Backward-compatible interface with original implementation
    """

    def __init__(
        self,
        target_tokens: int = 1000,
        max_tokens: int = 10000,
        overlap_pct: float = 0.15,
        min_chunk_tokens: int = 50,
        mode: Literal["semantic", "token", "auto"] = "semantic",
        embedding_model: str = "minishlab/potion-base-32M",
        similarity_threshold: float = 0.5
    ):
        """
        Initialize the hybrid chunker with configurable strategy.

        Args:
            target_tokens: Target chunk size in tokens (default: 1000)
            max_tokens: Hard maximum tokens per chunk (default: 10000)
            overlap_pct: Percentage of overlap between chunks for token mode (default: 0.15 = 15%)
            min_chunk_tokens: Minimum chunk size (default: 50)
            mode: Chunking strategy - "semantic", "token", or "auto" (default: "semantic")
                  - "semantic": Use semantic boundaries for coherent chunks
                  - "token": Use fixed token boundaries (faster, simpler)
                  - "auto": Use semantic for large docs, token for small docs
            embedding_model: Embedding model for semantic chunking (default: minishlab/potion-base-32M)
            similarity_threshold: Similarity threshold for semantic splitting (default: 0.5)
        """
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_pct = overlap_pct
        self.min_chunk_tokens = min_chunk_tokens
        self.mode = mode
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold

        # Initialize tiktoken encoder for token counting
        self.encoder = tiktoken.get_encoding("cl100k_base")

        # Initialize chunkers based on mode
        overlap_tokens = int(target_tokens * overlap_pct)

        if mode in ["semantic", "auto"]:
            # Initialize semantic chunker with embedding model
            try:
                logger.info("initializing_semantic_chunker",
                           embedding_model=embedding_model,
                           target_tokens=target_tokens,
                           threshold=similarity_threshold)

                self.semantic_chunker = ChonkieSemanticChunker(
                    embedding_model=embedding_model,
                    chunk_size=target_tokens,
                    threshold=similarity_threshold,
                    similarity_window=3,  # Look at 3 sentences for similarity
                    min_sentences_per_chunk=1,
                    min_characters_per_sentence=24
                )
                logger.info("semantic_chunker_initialized_successfully")
            except Exception as e:
                logger.error("semantic_chunker_initialization_failed",
                            error=str(e),
                            error_type=type(e).__name__)
                if mode == "semantic":
                    raise
                else:
                    logger.warning("falling_back_to_token_chunker")
                    self.mode = "token"

        if mode in ["token", "auto"] or not hasattr(self, 'semantic_chunker'):
            # Initialize token chunker as fallback or primary
            self.token_chunker = ChonkieTokenChunker(
                tokenizer="cl100k_base",
                chunk_size=target_tokens,
                chunk_overlap=overlap_tokens
            )
            logger.info("token_chunker_initialized",
                       target_tokens=target_tokens,
                       overlap_tokens=overlap_tokens)

        logger.info("chunker_initialized",
                   mode=self.mode,
                   target_tokens=target_tokens,
                   max_tokens=max_tokens,
                   library="chonkie")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken (compatibility method).

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

        Strategy (Hybrid Approach):
        1. Extract text from docling_output (markdown or json_content)
        2. Choose chunking strategy based on mode and document size
        3. Use semantic chunking for coherent boundaries OR token chunking for speed
        4. Enforce max_tokens hard limit (safety fallback)
        5. Log statistics

        Args:
            docling_output: Either DoclingParseResult or dict with md_content/json_content
            doc_id: Document ID
            user_id: User ID
            filename: Original filename

        Returns:
            List of ChunkMetadata objects
        """
        # Extract text content
        text = self._extract_text(docling_output)

        if not text or not text.strip():
            logger.warning("empty_document_skipping_chunking", doc_id=doc_id)
            return []

        text_tokens = self.count_tokens(text)
        logger.info("chunking_document",
                   doc_id=doc_id,
                   text_length=len(text),
                   text_tokens=text_tokens)

        # Determine which chunker to use
        use_semantic = self._should_use_semantic(text_tokens)

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

        # Log statistics
        self._log_statistics(chunk_metadatas, doc_id, oversized_count, chunking_mode)

        return chunk_metadatas

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

        This is a safety fallback that should rarely trigger - chonkie should
        respect chunk_size. If a chunk exceeds max_tokens, split at word boundaries.

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
        words = chunk.text.split()
        current_words = []
        current_tokens = 0
        sub_index = 0

        for word in words:
            word_with_space = word + " "
            word_tokens = self.count_tokens(word_with_space)

            if current_tokens + word_tokens <= self.max_tokens:
                current_words.append(word)
                current_tokens += word_tokens
            else:
                # Flush current chunk
                if current_words:
                    text = " ".join(current_words)
                    chunks.append(ChunkMetadata(
                        chunk_id=f"{doc_id}-chunk-{base_index:03d}-{sub_index}",
                        doc_id=doc_id,
                        user_id=user_id,
                        filename=filename,
                        section_title=None,
                        page_range=None,
                        chunk_index=base_index * 1000 + sub_index,
                        token_count=self.count_tokens(text),
                        text=text,
                        created_at=datetime.now(timezone.utc)
                    ))
                    sub_index += 1

                # Start new chunk with current word
                current_words = [word]
                current_tokens = word_tokens

        # Flush final chunk
        if current_words:
            text = " ".join(current_words)
            chunks.append(ChunkMetadata(
                chunk_id=f"{doc_id}-chunk-{base_index:03d}-{sub_index}",
                doc_id=doc_id,
                user_id=user_id,
                filename=filename,
                section_title=None,
                page_range=None,
                chunk_index=base_index * 1000 + sub_index,
                token_count=self.count_tokens(text),
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
