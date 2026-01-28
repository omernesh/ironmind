"""Tests for generator service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.generator import Generator, SYSTEM_PROMPT


class TestGenerator:
    """Test generator service."""

    def test_system_prompt_content(self):
        """Test system prompt includes grounding instructions."""
        assert "ONLY" in SYSTEM_PROMPT
        assert "citation" in SYSTEM_PROMPT.lower()
        assert "[1]" in SYSTEM_PROMPT or "citation numbers" in SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_generate_empty_chunks(self):
        """Test generation with no chunks returns 'no info' message."""
        generator = Generator()

        with patch.object(generator, 'client') as mock_client:
            result = await generator.generate(
                query="test question",
                chunks=[],
                request_id="test-123"
            )

        assert "cannot find" in result["answer"].lower()
        assert result["citations"] == []

    @pytest.mark.asyncio
    @patch('app.services.generator.AsyncOpenAI')
    async def test_generate_builds_context(self, mock_openai):
        """Test context building from chunks."""
        # Setup mock
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Answer [1]."))]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        generator = Generator()
        generator.client = mock_client

        chunks = [
            {
                "text": "Test content here",
                "doc_id": "doc-1",
                "filename": "test.pdf",
                "page_range": "1-2",
                "section_title": "Introduction",
                "rerank_score": 0.9
            }
        ]

        result = await generator.generate(
            query="What is the test about?",
            chunks=chunks,
            request_id="test-123"
        )

        # Verify context was built
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        # Should have system + user message
        assert len(messages) >= 2
        # User message should contain context
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "[1:" in user_msg["content"]
        assert "test.pdf" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_generate_builds_citations(self):
        """Test citation objects are built correctly."""
        generator = Generator()

        chunks = [
            {
                "text": "Content " * 50,  # Long content for snippet test
                "doc_id": "doc-1",
                "filename": "manual.pdf",
                "page_range": "42-43",
                "section_title": "Config",
                "rerank_score": 0.85
            }
        ]

        with patch.object(generator.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test [1]."))]
            mock_response.usage = MagicMock(total_tokens=50)
            mock_create.return_value = mock_response

            result = await generator.generate(
                query="test",
                chunks=chunks,
                request_id="test-123"
            )

        assert len(result["citations"]) == 1
        citation = result["citations"][0]
        assert citation.id == 1
        assert citation.doc_id == "doc-1"
        assert citation.filename == "manual.pdf"
        assert citation.page_range == "42-43"
        assert len(citation.snippet) <= 203  # 200 + "..."

    @pytest.mark.asyncio
    async def test_generate_with_history(self):
        """Test generation with conversation history."""
        generator = Generator()

        chunks = [
            {
                "text": "System has three layers",
                "doc_id": "doc-1",
                "filename": "architecture.pdf",
                "page_range": "5",
                "section_title": "Architecture",
                "rerank_score": 0.9
            }
        ]

        history = [
            {"role": "user", "content": "What is the system?"},
            {"role": "assistant", "content": "It's a network system."}
        ]

        with patch.object(generator.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Three layers [1]."))]
            mock_response.usage = MagicMock(total_tokens=75)
            mock_create.return_value = mock_response

            result = await generator.generate(
                query="Tell me more",
                chunks=chunks,
                request_id="test-456",
                history=history
            )

        # Verify history was included in messages
        call_args = mock_create.call_args
        messages = call_args.kwargs["messages"]

        # Should have: system + 2 history messages + current user message
        assert len(messages) >= 4
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What is the system?"
        assert messages[2]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_generate_returns_diagnostics(self):
        """Test that generation returns latency and token diagnostics."""
        generator = Generator()

        chunks = [
            {
                "text": "Test data",
                "doc_id": "doc-1",
                "filename": "test.pdf",
                "page_range": "1",
                "section_title": "Test",
                "rerank_score": 0.8
            }
        ]

        with patch.object(generator.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Answer."))]
            mock_response.usage = MagicMock(total_tokens=42)
            mock_create.return_value = mock_response

            result = await generator.generate(
                query="test",
                chunks=chunks,
                request_id="test-789"
            )

        # Verify diagnostics
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], int)
        assert result["latency_ms"] >= 0
        assert result["tokens_used"] == 42
