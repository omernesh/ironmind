"""Semantic chunking service for document sections."""
import hashlib
import tiktoken
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from app.core.logging import get_logger
from app.models.documents import ChunkMetadata

logger = get_logger()


class SemanticChunker:
    """
    Chunk documents by section boundaries with overlap.

    Strategy:
    1. Respect section boundaries (never split mid-section)
    2. Merge sections < 50 tokens with next section
    3. Split large sections at ~1000 token boundaries
    4. Add 10-20% overlap between consecutive chunks
    """

    def __init__(
        self,
        target_tokens: int = 1000,
        overlap_pct: float = 0.15,
        min_section_tokens: int = 50
    ):
        self.target_tokens = target_tokens
        self.overlap_pct = overlap_pct
        self.min_section_tokens = min_section_tokens
        # Use cl100k_base encoding (GPT-3.5/4 compatible)
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoder.encode(text))

    def chunk_document(
        self,
        docling_output: Dict[str, Any],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[ChunkMetadata]:
        """
        Chunk docling output into semantic chunks with metadata.

        Args:
            docling_output: Parsed document from docling-serve
            doc_id: Document ID
            user_id: User ID
            filename: Original filename

        Returns:
            List of ChunkMetadata with text and metadata
        """
        sections = self._extract_sections(docling_output)

        if not sections:
            logger.warning("no_sections_found", doc_id=doc_id)
            # Fallback: check for document.md_content or top-level text
            full_text = ""
            if "document" in docling_output:
                full_text = docling_output["document"].get("md_content", "")
            if not full_text:
                full_text = docling_output.get("text", "")
            if full_text:
                sections = [{"title": "Document", "text": full_text, "page_range": "1"}]

        # Merge small sections
        merged_sections = self._merge_small_sections(sections)

        # Split large sections
        split_sections = self._split_large_sections(merged_sections)

        # Create chunks with metadata
        chunks = self._create_chunks(split_sections, doc_id, user_id, filename)

        # Add overlap
        chunks_with_overlap = self._add_overlap(chunks)

        # Deduplicate
        unique_chunks = self._deduplicate(chunks_with_overlap)

        logger.info("chunking_completed",
                   doc_id=doc_id,
                   sections=len(sections),
                   chunks=len(unique_chunks))

        return unique_chunks

    def _extract_sections(self, docling_output: Dict) -> List[Dict]:
        """Extract sections from docling output format."""
        sections = []

        # Check for docling v1.10.0 format (document.md_content)
        if "document" in docling_output:
            doc = docling_output["document"]
            md_content = doc.get("md_content", "")
            if md_content:
                return self._parse_markdown_sections(md_content)

        # Docling may return different structures
        # Try common formats (fallback for other docling configurations)
        if "sections" in docling_output:
            for section in docling_output["sections"]:
                sections.append({
                    "title": section.get("heading", section.get("title", "")),
                    "text": section.get("text", section.get("content", "")),
                    "page_range": section.get("page_range",
                                             str(section.get("page", "")))
                })
        elif "pages" in docling_output:
            # Page-based structure
            for page in docling_output["pages"]:
                page_num = page.get("page_number", "")
                for block in page.get("blocks", []):
                    sections.append({
                        "title": block.get("heading", ""),
                        "text": block.get("text", ""),
                        "page_range": str(page_num)
                    })

        return sections

    def _parse_markdown_sections(self, md_content: str) -> List[Dict]:
        """Parse markdown content into sections by headings."""
        import re

        sections = []
        # Match markdown headings (# Heading, ## Subheading, etc.)
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

        # Find all headings and their positions
        headings = list(heading_pattern.finditer(md_content))

        if not headings:
            # No headings found - treat entire content as one section
            return [{"title": "Document", "text": md_content.strip(), "page_range": "1"}]

        for i, match in enumerate(headings):
            title = match.group(2).strip()
            start = match.end()

            # End is either next heading or end of document
            if i + 1 < len(headings):
                end = headings[i + 1].start()
            else:
                end = len(md_content)

            text = md_content[start:end].strip()

            # Estimate page number (rough: 3000 chars per page)
            page_estimate = max(1, (match.start() // 3000) + 1)

            if text:  # Only add sections with content
                sections.append({
                    "title": title,
                    "text": text,
                    "page_range": str(page_estimate)
                })

        return sections

    def _merge_small_sections(self, sections: List[Dict]) -> List[Dict]:
        """Merge sections smaller than min_section_tokens."""
        if not sections:
            return []

        merged = []
        current = None

        for section in sections:
            token_count = self.count_tokens(section["text"])

            if current is None:
                current = section.copy()
            elif token_count < self.min_section_tokens:
                # Merge with current
                current["text"] += "\n\n" + section["text"]
                if section["page_range"]:
                    current["page_range"] = self._merge_page_ranges(
                        current["page_range"], section["page_range"]
                    )
            else:
                # Current section is complete
                merged.append(current)
                current = section.copy()

        if current:
            merged.append(current)

        return merged

    def _split_large_sections(self, sections: List[Dict]) -> List[Dict]:
        """Split sections larger than 1.5x target into multiple chunks."""
        result = []
        max_tokens = int(self.target_tokens * 1.5)

        for section in sections:
            token_count = self.count_tokens(section["text"])

            if token_count <= max_tokens:
                result.append(section)
            else:
                # Split at paragraph boundaries
                paragraphs = section["text"].split("\n\n")
                current_text = ""
                current_tokens = 0
                chunk_idx = 0

                for para in paragraphs:
                    para_tokens = self.count_tokens(para)

                    if current_tokens + para_tokens > self.target_tokens and current_text:
                        result.append({
                            "title": f"{section['title']} (part {chunk_idx + 1})",
                            "text": current_text.strip(),
                            "page_range": section["page_range"]
                        })
                        current_text = para + "\n\n"
                        current_tokens = para_tokens
                        chunk_idx += 1
                    else:
                        current_text += para + "\n\n"
                        current_tokens += para_tokens

                if current_text.strip():
                    result.append({
                        "title": f"{section['title']} (part {chunk_idx + 1})" if chunk_idx > 0 else section["title"],
                        "text": current_text.strip(),
                        "page_range": section["page_range"]
                    })

        return result

    def _create_chunks(
        self,
        sections: List[Dict],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[ChunkMetadata]:
        """Create ChunkMetadata objects from sections."""
        chunks = []

        for idx, section in enumerate(sections):
            chunk_id = f"{doc_id}-chunk-{idx:03d}"
            token_count = self.count_tokens(section["text"])

            chunks.append(ChunkMetadata(
                chunk_id=chunk_id,
                doc_id=doc_id,
                user_id=user_id,
                filename=filename,
                section_title=section["title"],
                page_range=section["page_range"],
                chunk_index=idx,
                token_count=token_count,
                text=section["text"],
                created_at=datetime.now(timezone.utc)
            ))

        return chunks

    def _add_overlap(self, chunks: List[ChunkMetadata]) -> List[ChunkMetadata]:
        """Add overlap from previous chunk to current chunk."""
        if len(chunks) <= 1:
            return chunks

        overlap_tokens = int(self.target_tokens * self.overlap_pct)
        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_text = chunks[i-1].text
            prev_tokens = self.encoder.encode(prev_text)

            # Take last N tokens from previous chunk
            overlap_text = self.encoder.decode(prev_tokens[-overlap_tokens:]) if len(prev_tokens) > overlap_tokens else ""

            # Prepend to current chunk
            chunk = chunks[i]
            chunk.text = overlap_text + " " + chunk.text
            chunk.token_count = self.count_tokens(chunk.text)
            result.append(chunk)

        return result

    def _deduplicate(self, chunks: List[ChunkMetadata]) -> List[ChunkMetadata]:
        """Remove duplicate chunks by content hash."""
        seen_hashes = set()
        unique = []

        for chunk in chunks:
            # Normalize: lowercase, strip whitespace
            normalized = chunk.text.lower().strip()
            content_hash = hashlib.sha256(normalized.encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(chunk)

        if len(chunks) != len(unique):
            logger.info("chunks_deduplicated",
                       original=len(chunks),
                       unique=len(unique))

        return unique

    def _merge_page_ranges(self, range1: str, range2: str) -> str:
        """Merge two page ranges into a combined range."""
        try:
            # Parse ranges like "1-3" or "5"
            pages = set()
            for r in [range1, range2]:
                if "-" in r:
                    start, end = r.split("-")
                    pages.update(range(int(start), int(end) + 1))
                elif r.isdigit():
                    pages.add(int(r))

            if pages:
                return f"{min(pages)}-{max(pages)}"
        except:
            pass
        return range1 or range2
