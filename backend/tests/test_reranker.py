"""Tests for reranker service."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.reranker import Reranker


class TestReranker:
    """Test reranker service."""

    def test_reranker_init(self):
        """Test reranker initialization."""
        reranker = Reranker()
        assert "deepinfra" in reranker.model
        assert "Qwen" in reranker.model

    @pytest.mark.asyncio
    async def test_rerank_empty_chunks(self):
        """Test reranking empty list returns empty."""
        reranker = Reranker()
        result = await reranker.rerank(
            query="test query",
            chunks=[],
            request_id="test-123"
        )
        assert result["chunks"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    @patch('app.services.reranker.settings')
    @patch('app.services.reranker.rerank')
    async def test_rerank_success(self, mock_rerank, mock_settings):
        """Test successful reranking."""
        # Mock settings to have API key
        mock_settings.DEEPINFRA_API_KEY = "test-key"
        mock_settings.RERANK_LIMIT = 12

        # Mock litellm rerank response
        mock_result1 = MagicMock()
        mock_result1.index = 1
        mock_result1.relevance_score = 0.9

        mock_result2 = MagicMock()
        mock_result2.index = 0
        mock_result2.relevance_score = 0.7

        mock_response = MagicMock()
        mock_response.results = [mock_result1, mock_result2]
        mock_rerank.return_value = mock_response

        reranker = Reranker()
        chunks = [
            {"text": "chunk 1 content", "doc_id": "d1"},
            {"text": "chunk 2 content", "doc_id": "d2"},
        ]

        result = await reranker.rerank(
            query="test query",
            chunks=chunks,
            request_id="test-123",
            top_k=2
        )

        assert result["count"] == 2
        # Chunk 2 should be first (higher score)
        assert result["chunks"][0]["doc_id"] == "d2"
        assert result["chunks"][0]["rerank_score"] == 0.9
        assert result["chunks"][0]["rerank_rank"] == 1
        # Chunk 1 should be second
        assert result["chunks"][1]["doc_id"] == "d1"
        assert result["chunks"][1]["rerank_score"] == 0.7
        assert result["chunks"][1]["rerank_rank"] == 2

    @pytest.mark.asyncio
    @patch('app.services.reranker.settings')
    @patch('app.services.reranker.rerank')
    async def test_rerank_api_error_fallback(self, mock_rerank, mock_settings):
        """Test graceful fallback on API error."""
        # Mock settings to have API key
        mock_settings.DEEPINFRA_API_KEY = "test-key"
        mock_settings.RERANK_LIMIT = 12

        # Mock API error
        mock_rerank.side_effect = Exception("API connection failed")

        reranker = Reranker()
        chunks = [
            {"text": "chunk 1", "doc_id": "d1"},
            {"text": "chunk 2", "doc_id": "d2"}
        ]

        # Should not crash on API error
        result = await reranker.rerank(
            query="test",
            chunks=chunks,
            request_id="test-123",
            top_k=2
        )

        # Should return original chunks on error
        assert len(result["chunks"]) == 2
        assert result["chunks"][0]["doc_id"] == "d1"
        assert result["chunks"][1]["doc_id"] == "d2"

    @pytest.mark.asyncio
    @patch('app.config.settings.DEEPINFRA_API_KEY', '')
    async def test_rerank_missing_api_key(self):
        """Test handling of missing API key."""
        reranker = Reranker()
        chunks = [{"text": "chunk 1", "doc_id": "d1"}]

        # With missing API key, should return original chunks
        result = await reranker.rerank(
            query="test",
            chunks=chunks,
            request_id="test-123"
        )

        # Should return original chunks without calling API
        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["doc_id"] == "d1"

    @pytest.mark.asyncio
    @patch('app.services.reranker.settings')
    @patch('app.services.reranker.rerank')
    async def test_rerank_respects_top_k(self, mock_rerank, mock_settings):
        """Test that top_k parameter limits results."""
        # Mock settings to have API key
        mock_settings.DEEPINFRA_API_KEY = "test-key"
        mock_settings.RERANK_LIMIT = 12

        # Mock 3 results
        mock_results = []
        for i in range(3):
            mock_result = MagicMock()
            mock_result.index = i
            mock_result.relevance_score = 0.9 - (i * 0.1)
            mock_results.append(mock_result)

        mock_response = MagicMock()
        mock_response.results = mock_results
        mock_rerank.return_value = mock_response

        reranker = Reranker()
        chunks = [
            {"text": f"chunk {i}", "doc_id": f"d{i}"}
            for i in range(3)
        ]

        # Request only top 2
        result = await reranker.rerank(
            query="test query",
            chunks=chunks,
            request_id="test-123",
            top_k=2
        )

        # Verify top_k was passed to API
        mock_rerank.assert_called_once()
        call_args = mock_rerank.call_args
        assert call_args[1]["top_n"] == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rerank_real_api(self):
        """
        Integration test with real DeepInfra API.

        Requires DEEPINFRA_API_KEY in environment.
        Run with: pytest tests/test_reranker.py -m integration -v
        """
        from app.config import settings

        if not settings.DEEPINFRA_API_KEY:
            pytest.skip("DEEPINFRA_API_KEY not set")

        reranker = Reranker()
        chunks = [
            {"text": "The capital of France is Paris.", "doc_id": "d1"},
            {"text": "Python is a programming language.", "doc_id": "d2"},
            {"text": "Paris is the largest city in France.", "doc_id": "d3"},
        ]

        result = await reranker.rerank(
            query="What is the capital of France?",
            chunks=chunks,
            request_id="integration-test"
        )

        # Should return results
        assert result["count"] > 0
        assert len(result["chunks"]) > 0

        # First result should be most relevant (about Paris)
        top_chunk = result["chunks"][0]
        assert "Paris" in top_chunk["text"]
        assert "rerank_score" in top_chunk
        assert "rerank_rank" in top_chunk
        assert top_chunk["rerank_rank"] == 1
