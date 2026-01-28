"""Integration tests for chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


class TestChatEndpoint:
    """Test chat API endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication."""
        with patch('app.routers.chat.get_current_user_id') as mock:
            mock.return_value = "test-user-123"
            yield mock

    def test_chat_requires_auth(self, client):
        """Test chat endpoint requires authentication."""
        response = client.post("/api/chat", json={
            "question": "test",
            "user_id": "user-1"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_empty_results(self, client, mock_auth):
        """Test chat with no matching documents."""
        with patch('app.routers.chat.retriever') as mock_retriever:
            mock_retriever.retrieve = AsyncMock(return_value={
                "chunks": [],
                "count": 0,
                "latency_ms": 100
            })

            response = client.post("/api/chat", json={
                "question": "What is the weather?",
                "user_id": "test-user-123"
            })

            assert response.status_code == 200
            data = response.json()
            assert "couldn't find" in data["answer"].lower()
            assert data["citations"] == []
            assert data["diagnostics"]["retrieval_count"] == 0

    @pytest.mark.asyncio
    async def test_chat_full_pipeline(self, client, mock_auth):
        """Test full RAG pipeline execution."""
        with patch('app.routers.chat.retriever') as mock_retriever, \
             patch('app.routers.chat.reranker') as mock_reranker, \
             patch('app.routers.chat.generator') as mock_generator:

            # Mock retrieval
            mock_retriever.retrieve = AsyncMock(return_value={
                "chunks": [
                    {"text": "chunk 1", "doc_id": "d1", "filename": "test.pdf", "page_range": "1-2"}
                ],
                "count": 1,
                "latency_ms": 200
            })

            # Mock reranking
            mock_reranker.rerank = AsyncMock(return_value={
                "chunks": [
                    {"text": "chunk 1", "doc_id": "d1", "filename": "test.pdf", "page_range": "1-2", "rerank_score": 0.9}
                ],
                "count": 1,
                "latency_ms": 300
            })

            # Mock generation
            mock_generator.generate = AsyncMock(return_value={
                "answer": "Test answer [1].",
                "citations": [
                    {"id": 1, "doc_id": "d1", "filename": "test.pdf", "page_range": "1-2", "snippet": "chunk 1", "score": 0.9, "section_title": None}
                ],
                "latency_ms": 500
            })

            response = client.post("/api/chat", json={
                "question": "What is in the document?",
                "user_id": "test-user-123"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Test answer [1]."
            assert len(data["citations"]) == 1
            assert data["diagnostics"]["retrieval_count"] == 1
            assert data["diagnostics"]["total_latency_ms"] > 0

    def test_chat_request_validation(self, client, mock_auth):
        """Test request validation."""
        # Empty question
        response = client.post("/api/chat", json={
            "question": "",
            "user_id": "user-1"
        })
        assert response.status_code == 422  # Validation error

        # Missing user_id
        response = client.post("/api/chat", json={
            "question": "test question"
        })
        assert response.status_code == 422
