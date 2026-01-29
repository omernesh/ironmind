"""Integration tests for document chunking fix.

Tests verify:
1. Element-aware chunking produces reasonable chunk sizes
2. Tables are atomic (never split)
3. All chunks are under max_tokens limit
4. Fallback to markdown works correctly
"""
import pytest
from app.services.chunker import SemanticChunker
from app.models.documents import (
    DoclingTextElement,
    DoclingTableElement,
    DoclingHeadingElement,
    DoclingParseResult
)


class TestElementAwareChunking:
    """Test element-aware chunking algorithm."""

    def setup_method(self):
        self.chunker = SemanticChunker(
            target_tokens=1000,
            max_tokens=10000,
            overlap_pct=0.15
        )

    def test_basic_text_chunking(self):
        """Test chunking of basic text elements."""
        elements = [
            DoclingHeadingElement(text="Introduction", page_number=1, heading_level=1),
            DoclingTextElement(text="This is the introduction paragraph. " * 50, page_number=1),
            DoclingHeadingElement(text="Methods", page_number=2, heading_level=1),
            DoclingTextElement(text="This is the methods section. " * 50, page_number=2),
        ]
        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=2)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-001", "user-001", "test.pdf"
        )

        assert len(chunks) >= 2  # At least 2 sections
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens
            assert chunk.token_count > 0

    def test_table_atomicity(self):
        """Test that tables are never split."""
        # Create a large table (simulating ~5000 tokens)
        large_table_text = "| Col1 | Col2 | Col3 |\n" + "| data | data | data |\n" * 500
        elements = [
            DoclingTextElement(text="Before table.", page_number=1),
            DoclingTableElement(
                text=large_table_text,
                page_number=2,
                num_rows=501,
                num_cols=3
            ),
            DoclingTextElement(text="After table.", page_number=3),
        ]
        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=3)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-002", "user-001", "tables.pdf"
        )

        # Find the table chunk
        table_chunks = [c for c in chunks if "| Col1 |" in c.text]
        assert len(table_chunks) == 1  # Table should be single chunk
        assert "| data | data | data |" in table_chunks[0].text  # Complete table

    def test_max_tokens_enforced(self):
        """Test that no chunk exceeds max_tokens."""
        # Create very large text content
        huge_text = "word " * 20000  # ~20K tokens
        elements = [
            DoclingTextElement(text=huge_text, page_number=1),
        ]
        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=1)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-003", "user-001", "large.pdf"
        )

        # All chunks must be under max
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens, \
                f"Chunk {chunk.chunk_id} has {chunk.token_count} tokens, max is {self.chunker.max_tokens}"

    def test_section_boundaries(self):
        """Test that section headers create chunk boundaries."""
        elements = [
            DoclingHeadingElement(text="Section A", page_number=1, heading_level=1),
            DoclingTextElement(text="Content A. " * 100, page_number=1),
            DoclingHeadingElement(text="Section B", page_number=2, heading_level=1),
            DoclingTextElement(text="Content B. " * 100, page_number=2),
        ]
        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=2)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-004", "user-001", "sections.pdf"
        )

        # Should have chunks for each section
        section_titles = [c.section_title for c in chunks if c.section_title]
        assert "Section A" in section_titles or any("A" in t for t in section_titles)
        assert "Section B" in section_titles or any("B" in t for t in section_titles)

    def test_page_range_tracking(self):
        """Test that page ranges are tracked correctly."""
        elements = [
            DoclingTextElement(text="Page 1 content.", page_number=1),
            DoclingTextElement(text="Page 2 content.", page_number=2),
            DoclingTextElement(text="Page 3 content.", page_number=3),
        ]
        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=3)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-005", "user-001", "multi-page.pdf"
        )

        # At least one chunk should have page range
        page_ranges = [c.page_range for c in chunks if c.page_range]
        assert len(page_ranges) > 0


class TestMarkdownFallback:
    """Test fallback to markdown-based chunking."""

    def setup_method(self):
        self.chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

    def test_fallback_with_no_elements(self):
        """Test fallback when no structured elements."""
        docling_output = {
            "document": {
                "md_content": "# Introduction\n\nSome text here.\n\n# Methods\n\nMore text here."
            }
        }

        chunks = self.chunker.chunk_document(
            docling_output, "doc-006", "user-001", "markdown.pdf"
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens

    def test_fallback_with_large_markdown(self):
        """Test fallback handles large markdown content."""
        large_md = "# Title\n\n" + ("Paragraph text. " * 5000) + "\n\n# Section 2\n\n" + ("More text. " * 5000)
        docling_output = {
            "document": {"md_content": large_md}
        }

        chunks = self.chunker.chunk_document(
            docling_output, "doc-007", "user-001", "large-md.pdf"
        )

        # All chunks must be under max
        for chunk in chunks:
            assert chunk.token_count <= self.chunker.max_tokens


class TestChunkStatistics:
    """Test chunk statistics and validation."""

    def setup_method(self):
        self.chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

    def test_reasonable_chunk_distribution(self):
        """Test that chunk sizes are reasonably distributed."""
        # Create realistic document structure
        elements = []
        for i in range(10):
            elements.append(DoclingHeadingElement(
                text=f"Section {i+1}",
                page_number=i+1,
                heading_level=1
            ))
            # ~500-1500 tokens per section
            elements.append(DoclingTextElement(
                text="Content paragraph. " * (50 + i * 10),
                page_number=i+1
            ))

        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=10)

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

    def test_single_element(self):
        """Test document with single element."""
        elements = [DoclingTextElement(text="Just one paragraph.", page_number=1)]
        parse_result = DoclingParseResult(elements=elements, md_content="", page_count=1)

        chunks = self.chunker.chunk_document(
            parse_result, "doc-single", "user-001", "single.pdf"
        )

        assert len(chunks) == 1
        assert "Just one paragraph" in chunks[0].text

    def test_dict_input_compatibility(self):
        """Test backward compatibility with dict input."""
        docling_output = {
            "elements": [
                {"element_type": "text", "text": "Paragraph one.", "page_number": 1},
                {"element_type": "section_header", "text": "Section", "page_number": 1, "heading_level": 1},
                {"element_type": "text", "text": "Paragraph two.", "page_number": 2},
            ],
            "md_content": ""
        }

        chunks = self.chunker.chunk_document(
            docling_output, "doc-dict", "user-001", "dict.pdf"
        )

        assert len(chunks) >= 1


class TestEndToEndPipeline:
    """End-to-end pipeline tests for chunking fix."""

    @pytest.mark.asyncio
    async def test_simulated_aerospace_document(self):
        """
        Simulate processing a large aerospace document.

        This mimics the documents that were causing 300K-6.7M token chunks.
        The fix should produce chunks under 10K tokens.
        """
        from app.services.chunker import SemanticChunker

        chunker = SemanticChunker(target_tokens=1000, max_tokens=10000)

        # Simulate aerospace doc structure:
        # - Title page
        # - Table of contents (large)
        # - Multiple technical sections with tables
        # - Appendices
        elements = []

        # Title
        elements.append(DoclingHeadingElement(
            text="FC-001 Flight Control System Architecture",
            page_number=1,
            heading_level=1
        ))
        elements.append(DoclingTextElement(
            text="Document Version 2.3 | Classification: UNCLASSIFIED | Date: 2026-01-15",
            page_number=1
        ))

        # Table of contents (often causes issues)
        toc_text = "Table of Contents\n" + "\n".join([
            f"{i}. Section {i} .......................... {i*5}"
            for i in range(1, 50)
        ])
        elements.append(DoclingTableElement(
            text=toc_text,
            page_number=2,
            num_rows=50,
            num_cols=2
        ))

        # Technical sections with dense content
        for section_num in range(1, 20):
            elements.append(DoclingHeadingElement(
                text=f"Section {section_num}: System Component {section_num}",
                page_number=section_num * 3,
                heading_level=1
            ))

            # Dense technical paragraphs
            for para in range(5):
                tech_text = (
                    f"The {['IMU', 'GPS', 'FCS', 'AHRS', 'ADC'][para % 5]} subsystem "
                    f"interfaces with the primary flight computer via MIL-STD-1553B bus. "
                    f"Configuration parameters include tolerance thresholds, sampling rates, "
                    f"and fault detection algorithms. Refer to ICD-{section_num:03d} for details. "
                ) * 20
                elements.append(DoclingTextElement(
                    text=tech_text,
                    page_number=section_num * 3 + para
                ))

            # Add a specifications table every few sections
            if section_num % 3 == 0:
                table_text = "| Parameter | Min | Max | Unit |\n|---|---|---|---|\n"
                table_text += "\n".join([
                    f"| Param_{i} | {i*10} | {i*100} | unit_{i} |"
                    for i in range(30)
                ])
                elements.append(DoclingTableElement(
                    text=table_text,
                    page_number=section_num * 3 + 5,
                    num_rows=31,
                    num_cols=4
                ))

        parse_result = DoclingParseResult(
            elements=elements,
            md_content="",
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
