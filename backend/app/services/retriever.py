"""Hybrid retrieval service for RAG pipeline."""
import time
from typing import List, Dict, Any, Optional
from app.services.indexer import TxtaiIndexer
from app.config import settings
from app.core.logging import get_logger

logger = get_logger()

# Aerospace/defense domain acronyms for query expansion
ACRONYM_MAP = {
    "UAV": "Unmanned Aerial Vehicle",
    "IMU": "Inertial Measurement Unit",
    "GPS": "Global Positioning System",
    "INS": "Inertial Navigation System",
    "GNSS": "Global Navigation Satellite System",
    "RADAR": "Radio Detection and Ranging",
    "LIDAR": "Light Detection and Ranging",
    "EO": "Electro-Optical",
    "IR": "Infrared",
    "RF": "Radio Frequency",
    "C2": "Command and Control",
    "ISR": "Intelligence Surveillance Reconnaissance",
    "SATCOM": "Satellite Communications",
    "MTBF": "Mean Time Between Failures",
    "SWaP": "Size Weight and Power",
}


def preprocess_query(query: str) -> str:
    """
    Preprocess query with acronym expansion.

    Expands common aerospace/defense acronyms to improve semantic search.
    """
    import re

    def expand_acronym(match):
        acronym = match.group(0)
        if acronym in ACRONYM_MAP:
            return f"{acronym} ({ACRONYM_MAP[acronym]})"
        return acronym

    # Find uppercase acronyms (2+ letters)
    expanded = re.sub(r'\b[A-Z]{2,}\b', expand_acronym, query)
    return expanded.strip()


class HybridRetriever:
    """
    Hybrid retrieval combining semantic and BM25 search.

    Wraps TxtaiIndexer.hybrid_search() with query preprocessing,
    diagnostics logging, and structured response format.
    """

    def __init__(self, indexer: Optional[TxtaiIndexer] = None):
        self.indexer = indexer or TxtaiIndexer()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        request_id: str,
        limit: int = None,
        weights: float = None,
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks using hybrid search.

        Args:
            query: User's question
            user_id: User ID for filtering
            request_id: Request correlation ID
            limit: Override default retrieval limit
            weights: Override default hybrid weights
            threshold: Override default relevance threshold

        Returns:
            {
                "chunks": List of chunk dicts with metadata,
                "count": Number of chunks returned,
                "latency_ms": Retrieval time in ms,
                "diagnostics": {
                    "query_original": Original query,
                    "query_expanded": Query after acronym expansion,
                    "score_min": Minimum score in results,
                    "score_max": Maximum score in results,
                    "score_avg": Average score
                }
            }
        """
        start_time = time.time()

        # Apply defaults from settings
        limit = limit or settings.RETRIEVAL_LIMIT
        weights = weights if weights is not None else settings.HYBRID_WEIGHT
        threshold = threshold if threshold is not None else settings.RELEVANCE_THRESHOLD

        # Preprocess query with acronym expansion
        expanded_query = preprocess_query(query)

        logger.info("retrieval_started",
                   request_id=request_id,
                   user_id=user_id,
                   query_length=len(query),
                   expanded=expanded_query != query)

        # Call indexer.hybrid_search() - THE KEY WIRING
        chunks = self.indexer.hybrid_search(
            query=expanded_query,
            user_id=user_id,
            limit=limit,
            weights=weights,
            threshold=threshold
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Calculate score statistics for diagnostics
        scores = [c.get("score", 0) for c in chunks]
        diagnostics = {
            "query_original": query,
            "query_expanded": expanded_query,
            "score_min": min(scores) if scores else 0,
            "score_max": max(scores) if scores else 0,
            "score_avg": sum(scores) / len(scores) if scores else 0
        }

        logger.info("retrieval_complete",
                   request_id=request_id,
                   count=len(chunks),
                   latency_ms=latency_ms,
                   score_range=f"{diagnostics['score_min']:.3f}-{diagnostics['score_max']:.3f}")

        return {
            "chunks": chunks,
            "count": len(chunks),
            "latency_ms": latency_ms,
            "diagnostics": diagnostics
        }
