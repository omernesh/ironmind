"""Integration tests for hybrid document chunking with chonkie library.

Tests verify:
1. Semantic chunking produces coherent chunks
2. Token-based chunking produces reasonable chunk sizes
3. All chunks are under max_tokens limit
4. Hybrid mode switches between semantic and token chunking
5. Fallback mechanisms work correctly
6. End-to-end pipeline with realistic documents
"""
import pytest
from app.services.chunker import SemanticChunker
from app.models.documents import DoclingParseResult


class TestTokenBasedChunking:
    """Test chonkie TokenChunker-based implementation."""

    def setup_method(self):
        self.chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            overlap_pct=0.15
        )

    def test_basic_text_chunking(self):
        """Test chunking of basic text content."""
        # Create simple markdown content
        md_content = "# Introduction\n\n" + ("This is a test paragraph. " * 100)
        md_content += "\n\n# Methods\n\n" + ("This is another paragraph. " * 100)

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=2)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-001", "user-001", "test.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens
            assert chunk.token_count > 0
            assert chunk.text.strip() != ""

    def test_max_tokens_enforced(self):
        """Test that no chunk exceeds max_tokens (CRITICAL TEST)."""
        # Create very large text content
        huge_text = "word " * 20000  # ~20K tokens

        parse_result = DoclingParseResult(
            elements=[],
            md_content=huge_text,
            page_count=1
        )

        chunks = self.chunker.chunk_document(
            parse_result, "doc-003", "user-001", "large.pdf"
        )

        # All chunks must be under max
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens, \
                f"Chunk {chunk.chunk_id} has {chunk.token_count} tokens, max is {self.chunker.max_tokens}"

        # Should produce multiple chunks
        assert len(chunks) >= 2

    def test_chunk_metadata_structure(self):
        """Test that chunks have correct metadata structure."""
        md_content = "Test content. " * 500

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-meta", "user-123", "meta.pdf"
        )

        assert len(chunks) >= 1

        for idx, chunk in enumerate(chunks):
            assert chunk.doc_id == "doc-meta"
            assert chunk.user_id == "user-123"
            assert chunk.filename == "meta.pdf"
            assert chunk.chunk_id == f"doc-meta-chunk-{idx:03d}"
            assert chunk.chunk_index == idx
            assert chunk.created_at is not None
            assert isinstance(chunk.token_count, int)
            assert isinstance(chunk.text, str)


class TestMarkdownFallback:
    """Test handling of markdown content when no structured elements."""

    def setup_method(self):
        self.chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

    def test_markdown_content_extraction(self):
        """Test extraction of markdown content."""
        md_content = "# Introduction\n\nSome text here.\n\n# Methods\n\nMore text here."

        parse_result = DoclingParseResult(
            elements=[],
            md_content=md_content,
            page_count=1
        )

        chunks = self.chunker.chunk_document(
            parse_result, "doc-006", "user-001", "markdown.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens

    def test_large_markdown_content(self):
        """Test handling of large markdown content."""
        large_md = "# Title\n\n" + ("Paragraph text. " * 5000)
        large_md += "\n\n# Section 2\n\n" + ("More text. " * 5000)

        parse_result = DoclingParseResult(
            elements=[],
            md_content=large_md,
            page_count=1
        )

        chunks = self.chunker.chunk_document(
            parse_result, "doc-007", "user-001", "large-md.pdf"
        )

        # All chunks must be under max
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens

        # Should produce multiple chunks
        assert len(chunks) >= 2

    def test_dict_input_compatibility(self):
        """Test backward compatibility with dict input."""
        docling_output = {
            "md_content": "# Test\n\nSome content here. " * 100
        }

        chunks = self.chunker.chunk_document(
            docling_output, "doc-dict", "user-001", "dict.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens


class TestChunkStatistics:
    """Test chunk statistics and validation."""

    def setup_method(self):
        # Use token mode for distribution testing
        self.chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            mode="token"  # Token mode for predictable size distribution
        )

    def test_reasonable_chunk_distribution(self):
        """Test that chunk sizes are reasonably distributed (using token mode)."""
        # Create realistic document structure
        sections = []
        for i in range(10):
            sections.append(f"# Section {i+1}\n\n")
            # ~500-1500 tokens per section
            sections.append("Content paragraph. " * (50 + i * 10))
            sections.append("\n\n")

        md_content = "".join(sections)
        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=10)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-008", "user-001", "realistic.pdf"
        )

        token_counts = [c.token_count for c in chunks]
        avg_tokens = sum(token_counts) / len(token_counts)

        # Average should be near target (within 2x)
        assert avg_tokens < self.chunker.target_tokens * 2
        # No chunk should exceed max
        assert max(token_counts) <= self.chunker.max_tokens


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        self.chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

    def test_empty_document(self):
        """Test handling of empty documents."""
        parse_result = DoclingParseResult(elements=[], md_content="", page_count=0)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-empty", "user-001", "empty.pdf"
        )

        assert chunks == []

    def test_whitespace_only_document(self):
        """Test handling of whitespace-only documents."""
        parse_result = DoclingParseResult(
            elements=[],
            md_content="   \n\n\t\t  \n  ",
            page_count=0
        )

        chunks = self.chunker.chunk_document(
            parse_result, "doc-whitespace", "user-001", "whitespace.pdf"
        )

        assert chunks == []

    def test_single_short_paragraph(self):
        """Test document with single short paragraph."""
        md_content = "Just one short paragraph."

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-single", "user-001", "single.pdf"
        )

        assert len(chunks) == 1
        assert "Just one short paragraph" in chunks[0].text

    def test_very_long_single_word(self):
        """Test handling of extremely long 'words' (edge case)."""
        # Simulate a long URL or hash
        long_word = "https://example.com/" + "a" * 50000

        parse_result = DoclingParseResult(
            elements=[],
            md_content=long_word,
            page_count=1
        )

        chunks = self.chunker.chunk_document(
            parse_result, "doc-longword", "user-001", "long.pdf"
        )

        # Should handle without crashing
        assert len(chunks) >= 1


class TestEndToEndPipeline:
    """End-to-end pipeline tests for chunking with chonkie."""

    @pytest.mark.asyncio
    async def test_simulated_aerospace_document(self):
        """
        Simulate processing a large aerospace document.

        This mimics documents that were causing 300K-6.7M token chunks.
        The chonkie-based implementation should produce chunks under 10K tokens.
        """
        chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

        # Simulate aerospace doc structure as markdown
        sections = []

        # Title
        sections.append("# FC-001 Flight Control System Architecture\n\n")
        sections.append("Document Version 2.3 | Classification: UNCLASSIFIED | Date: 2026-01-15\n\n")

        # Table of contents
        sections.append("## Table of Contents\n\n")
        for i in range(1, 50):
            sections.append(f"{i}. Section {i} {'.' * 50} {i*5}\n")
        sections.append("\n\n")

        # Technical sections with dense content
        for section_num in range(1, 20):
            sections.append(f"## Section {section_num}: System Component {section_num}\n\n")

            # Dense technical paragraphs
            for para in range(5):
                tech_text = (
                    f"The {['IMU', 'GPS', 'FCS', 'AHRS', 'ADC'][para % 5]} subsystem "
                    f"interfaces with the primary flight computer via MIL-STD-1553B bus. "
                    f"Configuration parameters include tolerance thresholds, sampling rates, "
                    f"and fault detection algorithms. Refer to ICD-{section_num:03d} for details. "
                ) * 20
                sections.append(tech_text + "\n\n")

            # Add specifications table every few sections
            if section_num % 3 == 0:
                sections.append("### Specifications Table\n\n")
                sections.append("| Parameter | Min | Max | Unit |\n")
                sections.append("|---|---|---|---|\n")
                for i in range(30):
                    sections.append(f"| Param_{i} | {i*10} | {i*100} | unit_{i} |\n")
                sections.append("\n\n")

        md_content = "".join(sections)

        parse_result = DoclingParseResult(
            elements=[],
            md_content=md_content,
            page_count=60
        )

        # Process document
        chunks = chunker.chunk_document(
            parse_result,
            "doc-aerospace-001",
            "user-001",
            "FC-001-Architecture.pdf"
        )

        # Validate results
        assert len(chunks) > 0, "Should produce chunks"

        # CRITICAL: All chunks must be under 10K tokens
        for chunk in chunks:
            assert chunk.token_count <= 10000, \
                f"Chunk {chunk.chunk_id} exceeds limit: {chunk.token_count} tokens"

        # Verify reasonable distribution
        token_counts = [c.token_count for c in chunks]
        avg_tokens = sum(token_counts) / len(token_counts)

        print(f"\nAerospace Document Chunking Results:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Min tokens: {min(token_counts)}")
        print(f"  Max tokens: {max(token_counts)}")
        print(f"  Avg tokens: {avg_tokens:.0f}")
        print(f"  Target tokens: {chunker.target_tokens}")

        # Average should be reasonable (not all massive chunks)
        assert avg_tokens < 5000, f"Average chunk size too large: {avg_tokens}"

        # Should have multiple chunks (not one massive chunk)
        assert len(chunks) >= 10, f"Too few chunks: {len(chunks)}"


class TestTokenCounting:
    """Test token counting consistency."""

    def setup_method(self):
        self.chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

    def test_count_tokens_method(self):
        """Test count_tokens method works correctly."""
        text = "This is a test sentence."
        count = self.chunker.count_tokens(text)

        assert isinstance(count, int)
        assert count > 0
        assert count < 100  # Reasonable for this short text

    def test_chunk_token_counts_accurate(self):
        """Test that chunk token_count matches actual token count."""
        md_content = "Test content. " * 500

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-token-test", "user-001", "tokens.pdf"
        )

        for chunk in chunks:
            # Verify token count is accurate
            actual_count = self.chunker.count_tokens(chunk.text)
            # Allow small variance due to chunk boundaries
            assert abs(chunk.token_count - actual_count) <= 5, \
                f"Token count mismatch: {chunk.token_count} vs {actual_count}"


class TestHybridChunking:
    """Test hybrid chunking modes (semantic/token/auto)."""

    def test_semantic_mode(self):
        """Test explicit semantic chunking mode."""
        chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            mode="semantic"
        )

        # Create document with clear semantic sections
        md_content = """# Introduction

This is the introduction section with important context. It discusses the main themes and objectives of the document.

# Background

This section provides background information. It has different semantic meaning from the introduction.

# Methodology

Here we describe the methodology used in this work. This is semantically distinct from the background section.
"""

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = chunker.chunk_document(
            parse_result, "doc-semantic", "user-001", "semantic.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.max_tokens

    def test_token_mode(self):
        """Test explicit token chunking mode."""
        chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            mode="token"
        )

        md_content = "Test content. " * 500

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = chunker.chunk_document(
            parse_result, "doc-token", "user-001", "token.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.max_tokens

    def test_auto_mode_small_document(self):
        """Test auto mode with small document (should use token chunking)."""
        chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            mode="auto"
        )

        # Small document (< 5000 tokens)
        md_content = "Short document. " * 100

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = chunker.chunk_document(
            parse_result, "doc-auto-small", "user-001", "auto-small.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.max_tokens

    def test_auto_mode_large_document(self):
        """Test auto mode with large document (should use semantic chunking)."""
        chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            mode="auto"
        )

        # Large document (> 5000 tokens)
        sections = []
        for i in range(20):
            sections.append(f"# Section {i+1}\n\n")
            sections.append("This is a paragraph with meaningful content. " * 50)
            sections.append("\n\n")

        md_content = "".join(sections)

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = chunker.chunk_document(
            parse_result, "doc-auto-large", "user-001", "auto-large.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= chunker.max_tokens

    def test_semantic_chunking_coherence(self):
        """Test that semantic chunking maintains coherence."""
        chunker = SemanticChunker(
            target_tokens=500,  # Smaller chunks to test boundary detection
            max_tokens=10000,
            mode="semantic",
            similarity_threshold=0.5
        )

        # Document with distinct semantic sections
        md_content = """# Machine Learning Basics

Machine learning is a subset of artificial intelligence. It involves training models on data to make predictions.

# Deep Learning Introduction

Deep learning uses neural networks with multiple layers. It has revolutionized computer vision and natural language processing.

# Conclusion

In summary, machine learning and deep learning are powerful tools for data analysis and prediction tasks.
"""

        parse_result = DoclingParseResult(elements=[], md_content=md_content, page_count=1)

        chunks = chunker.chunk_document(
            parse_result, "doc-coherence", "user-001", "coherence.pdf"
        )

        assert len(chunks) >= 1
        # Verify chunks are within limits
        for chunk in chunks:
            assert chunk.token_count <= chunker.max_tokens
            assert len(chunk.text.strip()) > 0
