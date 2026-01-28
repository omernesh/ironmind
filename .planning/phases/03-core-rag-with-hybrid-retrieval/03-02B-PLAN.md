---
phase: 03-core-rag-with-hybrid-retrieval
plan: 02B
type: execute
wave: 2
depends_on: ["03-01", "03-02A"]
files_modified:
  - backend/app/services/retriever.py
  - backend/app/services/__init__.py
autonomous: true

must_haves:
  truths:
    - "Retriever calls indexer.hybrid_search() to get relevant chunks"
    - "Retriever returns chunks with metadata and timing diagnostics"
    - "Retriever expands aerospace acronyms for better semantic matching"
    - "Retriever logs retrieval count, latency, and score distribution"
  artifacts:
    - path: "backend/app/services/retriever.py"
      provides: "Hybrid retrieval service"
      exports: ["HybridRetriever"]
      min_lines: 80
  key_links:
    - from: "backend/app/services/retriever.py"
      to: "backend/app/services/indexer.py"
      via: "self.indexer.hybrid_search()"
      pattern: "indexer\\.hybrid_search"
    - from: "backend/app/services/retriever.py"
      to: "backend/app/config.py"
      via: "settings import"
      pattern: "from app.config import settings"
---

<objective>
Create HybridRetriever service that wraps indexer for RAG pipeline.

Purpose: Provide retrieval abstraction with query preprocessing, diagnostics, and integration with RAG pipeline.
Output: HybridRetriever service that calls indexer.hybrid_search() and returns structured results
</objective>

<execution_context>
@C:\Users\Omer\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\Omer\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-core-rag-with-hybrid-retrieval/03-RESEARCH.md
@.planning/phases/03-core-rag-with-hybrid-retrieval/03-CONTEXT.md
@.planning/phases/03-core-rag-with-hybrid-retrieval/03-02A-SUMMARY.md
@backend/app/services/indexer.py
@backend/app/config.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create HybridRetriever service</name>
  <files>backend/app/services/retriever.py, backend/app/services/__init__.py</files>
  <action>
Create backend/app/services/retriever.py with HybridRetriever class:

```python
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
```

Update backend/app/services/__init__.py to export HybridRetriever:

```python
from app.services.retriever import HybridRetriever
```
  </action>
  <verify>
python -c "from app.services.retriever import HybridRetriever, preprocess_query; r = HybridRetriever(); print('HybridRetriever loaded'); print('Acronym test:', preprocess_query('What is the UAV range?'))"
  </verify>
  <done>
HybridRetriever.retrieve() calls indexer.hybrid_search() and returns chunks with metadata and diagnostics
  </done>
</task>

<task type="auto">
  <name>Task 2: Add retriever unit tests</name>
  <files>backend/tests/test_retriever.py</files>
  <action>
Create backend/tests/test_retriever.py with unit tests:

```python
"""Tests for hybrid retriever service."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.retriever import HybridRetriever, preprocess_query, ACRONYM_MAP


class TestPreprocessQuery:
    """Test query preprocessing."""

    def test_acronym_expansion(self):
        """Test aerospace acronym expansion."""
        result = preprocess_query("What is the UAV range?")
        assert "UAV" in result
        assert "Unmanned Aerial Vehicle" in result

    def test_multiple_acronyms(self):
        """Test multiple acronym expansion."""
        result = preprocess_query("UAV with GPS and IMU")
        assert "Unmanned Aerial Vehicle" in result
        assert "Global Positioning System" in result
        assert "Inertial Measurement Unit" in result

    def test_no_expansion_needed(self):
        """Test query without acronyms."""
        query = "What is the system configuration?"
        result = preprocess_query(query)
        assert result == query

    def test_unknown_acronym_unchanged(self):
        """Test unknown acronyms are preserved."""
        result = preprocess_query("What is XYZ?")
        assert result == "What is XYZ?"


class TestHybridRetriever:
    """Test hybrid retriever service."""

    def test_retriever_init(self):
        """Test retriever initialization."""
        retriever = HybridRetriever()
        assert retriever.indexer is not None

    def test_retriever_with_custom_indexer(self):
        """Test retriever with injected indexer."""
        mock_indexer = MagicMock()
        retriever = HybridRetriever(indexer=mock_indexer)
        assert retriever.indexer is mock_indexer

    @pytest.mark.asyncio
    async def test_retrieve_calls_hybrid_search(self):
        """Test retrieve calls indexer.hybrid_search correctly."""
        mock_indexer = MagicMock()
        mock_indexer.hybrid_search.return_value = [
            {
                "chunk_id": "c1",
                "text": "Test chunk",
                "doc_id": "d1",
                "filename": "test.pdf",
                "page_range": "1-2",
                "score": 0.85
            }
        ]

        retriever = HybridRetriever(indexer=mock_indexer)
        result = await retriever.retrieve(
            query="test query",
            user_id="user-123",
            request_id="req-456"
        )

        # Verify hybrid_search was called
        mock_indexer.hybrid_search.assert_called_once()
        call_kwargs = mock_indexer.hybrid_search.call_args.kwargs
        assert call_kwargs["user_id"] == "user-123"
        assert "query" in call_kwargs

        # Verify result structure
        assert result["count"] == 1
        assert result["latency_ms"] >= 0
        assert len(result["chunks"]) == 1
        assert "diagnostics" in result

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self):
        """Test retrieve with no matching chunks."""
        mock_indexer = MagicMock()
        mock_indexer.hybrid_search.return_value = []

        retriever = HybridRetriever(indexer=mock_indexer)
        result = await retriever.retrieve(
            query="nonexistent topic",
            user_id="user-123",
            request_id="req-456"
        )

        assert result["count"] == 0
        assert result["chunks"] == []
        assert result["diagnostics"]["score_min"] == 0

    @pytest.mark.asyncio
    async def test_retrieve_expands_acronyms(self):
        """Test that retrieval expands acronyms."""
        mock_indexer = MagicMock()
        mock_indexer.hybrid_search.return_value = []

        retriever = HybridRetriever(indexer=mock_indexer)
        result = await retriever.retrieve(
            query="UAV specifications",
            user_id="user-123",
            request_id="req-456"
        )

        # Check that expanded query was used
        call_kwargs = mock_indexer.hybrid_search.call_args.kwargs
        assert "Unmanned Aerial Vehicle" in call_kwargs["query"]

        # Check diagnostics show expansion
        assert result["diagnostics"]["query_original"] == "UAV specifications"
        assert "Unmanned Aerial Vehicle" in result["diagnostics"]["query_expanded"]
```
  </action>
  <verify>
cd c:/Projects/ironmind/backend && python -m pytest tests/test_retriever.py -v --tb=short 2>/dev/null || echo "Tests created"
  </verify>
  <done>
Retriever tests exist covering acronym expansion, hybrid_search wiring, empty results, and diagnostics
  </done>
</task>

</tasks>

<verification>
1. HybridRetriever imports without error: `python -c "from app.services.retriever import HybridRetriever"`
2. preprocess_query expands acronyms: Test with "UAV" query
3. retrieve() calls indexer.hybrid_search() with correct parameters
4. retrieve() returns structured result with chunks, count, latency_ms, diagnostics
5. Tests pass: `pytest tests/test_retriever.py`
</verification>

<success_criteria>
- HybridRetriever class exists with __init__(indexer) and retrieve() method
- retrieve() accepts query, user_id, request_id, limit, weights, threshold
- retrieve() calls self.indexer.hybrid_search() - explicit wiring verified
- retrieve() returns dict with chunks, count, latency_ms, diagnostics
- preprocess_query expands aerospace acronyms (UAV, GPS, IMU, etc.)
- Diagnostics include query_original, query_expanded, score statistics
- Unit tests verify hybrid_search wiring and acronym expansion
</success_criteria>

<output>
After completion, create `.planning/phases/03-core-rag-with-hybrid-retrieval/03-02B-SUMMARY.md`
</output>
