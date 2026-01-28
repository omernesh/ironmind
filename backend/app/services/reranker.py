"""Reranker service using DeepInfra Qwen3-Reranker."""
import os
import time
from typing import List, Dict, Any
from litellm import rerank
from app.config import settings
from app.core.logging import get_logger

logger = get_logger()


class Reranker:
    """
    Reranker using DeepInfra Qwen3-Reranker model.

    Note: Research confirmed that Mistral does NOT have a dedicated reranking model.
    DeepInfra provides Qwen3-Reranker variants (0.6B, 4B, 8B).
    Using 0.6B for speed (1-2s latency target).

    See REQUIREMENTS.md RETRIEVAL-08 for configuration details.
    """

    def __init__(self):
        # Set DeepInfra API key for litellm
        os.environ["DEEPINFRA_API_KEY"] = settings.DEEPINFRA_API_KEY
        self.model = f"deepinfra/{settings.RERANK_MODEL}"

    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        request_id: str,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Rerank chunks using cross-encoder model.

        Args:
            query: User's question
            chunks: List of chunk dicts with 'text' field
            request_id: Request correlation ID
            top_k: Return top K chunks (default: settings.RERANK_LIMIT)

        Returns:
            {
                "chunks": Reranked list with rerank_score added,
                "count": Number of chunks returned,
                "latency_ms": Reranking time in ms
            }
        """
        # Handle empty input
        if not chunks:
            return {
                "chunks": [],
                "count": 0,
                "latency_ms": 0
            }

        # Check API key is set
        if not settings.DEEPINFRA_API_KEY:
            logger.error(
                "deepinfra_api_key_missing",
                request_id=request_id,
                message="DEEPINFRA_API_KEY not set, skipping reranking"
            )
            return {
                "chunks": chunks,
                "count": len(chunks),
                "latency_ms": 0
            }

        # Default top_k to settings
        if top_k is None:
            top_k = settings.RERANK_LIMIT

        start_time = time.time()

        try:
            # Extract text from chunks for reranker input
            documents = [chunk.get("text", "") for chunk in chunks]

            # Call litellm rerank
            logger.info(
                "rerank_started",
                request_id=request_id,
                model=self.model,
                num_chunks=len(chunks),
                top_k=top_k
            )

            response = rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_k
            )

            # Map reranker results back to original chunks
            reranked_chunks = []
            scores = []

            for rank, result in enumerate(response.results):
                # Get original chunk by index
                original_chunk = chunks[result.index].copy()

                # Add reranking metadata
                original_chunk["rerank_score"] = result.relevance_score
                original_chunk["rerank_rank"] = rank + 1

                reranked_chunks.append(original_chunk)
                scores.append(result.relevance_score)

            latency_ms = int((time.time() - start_time) * 1000)

            # Log diagnostics
            logger.info(
                "rerank_completed",
                request_id=request_id,
                latency_ms=latency_ms,
                input_count=len(chunks),
                output_count=len(reranked_chunks),
                score_min=min(scores) if scores else 0,
                score_max=max(scores) if scores else 0,
                score_avg=sum(scores) / len(scores) if scores else 0
            )

            return {
                "chunks": reranked_chunks,
                "count": len(reranked_chunks),
                "latency_ms": latency_ms
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            logger.warning(
                "rerank_failed",
                request_id=request_id,
                error=str(e),
                latency_ms=latency_ms,
                message="Reranking failed, returning original order"
            )

            # Graceful fallback: return original chunks without reranking
            return {
                "chunks": chunks[:top_k],
                "count": len(chunks[:top_k]),
                "latency_ms": latency_ms
            }
