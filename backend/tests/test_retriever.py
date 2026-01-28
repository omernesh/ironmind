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
