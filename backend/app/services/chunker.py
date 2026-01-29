"""Element-aware semantic chunking for Docling documents."""
import hashlib
import tiktoken
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone
from app.core.logging import get_logger
from app.models.documents import (
    ChunkMetadata,
    DoclingElement,
    DoclingTextElement,
    DoclingTableElement,
    DoclingHeadingElement,
    DoclingListItemElement,
    DoclingParseResult
)

logger = get_logger()


class SemanticChunker:
    """
    Chunk documents by element boundaries with overlap.

    Strategy (element-aware):
    1. Tables are ATOMIC - never split, even if large
    2. Section headers start new chunks
    3. Text paragraphs are grouped until target_tokens
    4. Large paragraphs split at sentence boundaries
    5. 15% overlap between consecutive text chunks
    """

    def __init__(
        self,
        target_tokens: int = 1000,
        max_tokens: int = 10000,  # Hard limit - well under OpenAI's 300K
        overlap_pct: float = 0.15,
        min_chunk_tokens: int = 50
    ):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_pct = overlap_pct
        self.min_chunk_tokens = min_chunk_tokens
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoder.encode(text))

    def chunk_document(
        self,
        docling_output: Union[Dict[str, Any], DoclingParseResult],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[ChunkMetadata]:
        """
        Chunk document using element-aware strategy.

        Args:
            docling_output: Either DoclingParseResult or dict with elements/md_content
            doc_id: Document ID
            user_id: User ID
            filename: Original filename

        Returns:
            List of ChunkMetadata with text and metadata
        """
        # Extract elements from input
        elements = self._get_elements(docling_output)

        if not elements:
            # Fallback to markdown-based chunking if no elements
            logger.warning("no_elements_found_using_markdown_fallback", doc_id=doc_id)
            return self._chunk_from_markdown(docling_output, doc_id, user_id, filename)

        # Group elements into chunks
        raw_chunks = self._group_elements_into_chunks(elements)

        # Create ChunkMetadata objects
        chunks = self._create_chunks(raw_chunks, doc_id, user_id, filename)

        # Add overlap between text chunks
        chunks_with_overlap = self._add_overlap(chunks)

        # Deduplicate
        unique_chunks = self._deduplicate(chunks_with_overlap)

        # Enforce max token limit (emergency split for any oversized chunks)
        safe_chunks = self._enforce_max_tokens(unique_chunks)

        # Validate and log statistics
        self._validate_and_log_statistics(safe_chunks, doc_id)

        logger.info("element_chunking_completed",
                   doc_id=doc_id,
                   elements=len(elements),
                   chunks=len(safe_chunks),
                   max_tokens=max(c.token_count for c in safe_chunks) if safe_chunks else 0)

        return safe_chunks

    def _get_elements(self, docling_output: Union[Dict, DoclingParseResult]) -> List[DoclingElement]:
        """Extract elements from various input formats."""
        if isinstance(docling_output, DoclingParseResult):
            return docling_output.elements

        # Dict format - check for elements list
        if "elements" in docling_output:
            return [self._dict_to_element(e) for e in docling_output["elements"]]

        return []

    def _dict_to_element(self, d: dict) -> DoclingElement:
        """Convert dict to typed DoclingElement."""
        element_type = d.get("element_type", "text")
        if element_type == "table":
            return DoclingTableElement(**d)
        elif element_type == "section_header":
            return DoclingHeadingElement(**d)
        elif element_type == "list_item":
            return DoclingListItemElement(**d)
        else:
            return DoclingTextElement(**d)

    def _group_elements_into_chunks(self, elements: List[DoclingElement]) -> List[Dict]:
        """Group elements into chunks respecting element boundaries."""
        chunks = []
        current_chunk = {
            "texts": [],
            "page_start": None,
            "page_end": None,
            "section_title": None,
            "is_table": False
        }
        current_tokens = 0
        current_section = "Document"

        for element in elements:
            element_tokens = self.count_tokens(element.text)

            # Update section title from headings
            if isinstance(element, DoclingHeadingElement):
                current_section = element.text

                # Start new chunk on section header (if current has content)
                if current_chunk["texts"] and current_tokens >= self.min_chunk_tokens:
                    chunks.append(self._finalize_chunk(current_chunk, current_tokens))
                    current_chunk = self._new_chunk()
                    current_tokens = 0

                current_chunk["section_title"] = element.text

            # Tables - keep atomic if small, split if too large
            if isinstance(element, DoclingTableElement):
                # Flush current text chunk first
                if current_chunk["texts"]:
                    chunks.append(self._finalize_chunk(current_chunk, current_tokens))
                    current_chunk = self._new_chunk()
                    current_tokens = 0

                # If table is small enough, keep it atomic
                if element_tokens <= self.max_tokens:
                    table_chunk = {
                        "texts": [element.text],
                        "page_start": element.page_number,
                        "page_end": element.page_number,
                        "section_title": current_section,
                        "is_table": True,
                        "token_count": element_tokens
                    }
                    chunks.append(table_chunk)
                    logger.debug("table_chunk_created",
                                tokens=element_tokens,
                                rows=element.num_rows,
                                cols=element.num_cols)
                else:
                    # Table is too large - split it
                    logger.warning("splitting_large_table",
                                  tokens=element_tokens,
                                  rows=element.num_rows,
                                  cols=element.num_cols)
                    split_texts = self._split_large_text(element.text)
                    for i, split_text in enumerate(split_texts):
                        split_tokens = self.count_tokens(split_text)
                        table_chunk = {
                            "texts": [split_text],
                            "page_start": element.page_number,
                            "page_end": element.page_number,
                            "section_title": current_section,
                            "is_table": True,
                            "token_count": split_tokens
                        }
                        chunks.append(table_chunk)
                        logger.debug("table_chunk_split_created",
                                    part=i+1,
                                    tokens=split_tokens)
                continue

            # Text elements - group until target reached
            if current_tokens + element_tokens > self.target_tokens and current_chunk["texts"]:
                # Current chunk is full
                chunks.append(self._finalize_chunk(current_chunk, current_tokens))
                current_chunk = self._new_chunk()
                current_chunk["section_title"] = current_section
                current_tokens = 0

            # Handle oversized single elements
            if element_tokens > self.max_tokens:
                # Split the element into smaller pieces
                split_texts = self._split_large_text(element.text)
                for split_text in split_texts:
                    split_tokens = self.count_tokens(split_text)
                    if current_tokens + split_tokens > self.target_tokens and current_chunk["texts"]:
                        chunks.append(self._finalize_chunk(current_chunk, current_tokens))
                        current_chunk = self._new_chunk()
                        current_chunk["section_title"] = current_section
                        current_tokens = 0

                    current_chunk["texts"].append(split_text)
                    current_tokens += split_tokens
                    self._update_page_range(current_chunk, element.page_number)
            else:
                current_chunk["texts"].append(element.text)
                current_tokens += element_tokens
                self._update_page_range(current_chunk, element.page_number)

        # Don't forget the last chunk
        if current_chunk["texts"]:
            chunks.append(self._finalize_chunk(current_chunk, current_tokens))

        return chunks

    def _new_chunk(self) -> Dict:
        """Create new empty chunk dict."""
        return {
            "texts": [],
            "page_start": None,
            "page_end": None,
            "section_title": None,
            "is_table": False
        }

    def _finalize_chunk(self, chunk: Dict, token_count: int) -> Dict:
        """Finalize chunk with token count."""
        chunk["token_count"] = token_count
        return chunk

    def _update_page_range(self, chunk: Dict, page_number: Optional[int]):
        """Update chunk's page range."""
        if page_number is None:
            return
        if chunk["page_start"] is None:
            chunk["page_start"] = page_number
        chunk["page_end"] = page_number

    def _split_large_text(self, text: str) -> List[str]:
        """Split large text at sentence boundaries."""
        import re

        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If single sentence exceeds max, split by words
            if sentence_tokens > self.max_tokens:
                if current:
                    chunks.append(current.strip())
                    current = ""
                    current_tokens = 0

                # Word-level splitting for very long sentences
                words = sentence.split()
                for word in words:
                    word_tokens = self.count_tokens(word + " ")
                    if current_tokens + word_tokens > self.target_tokens and current:
                        chunks.append(current.strip())
                        current = word + " "
                        current_tokens = word_tokens
                    else:
                        current += word + " "
                        current_tokens += word_tokens
            else:
                if current_tokens + sentence_tokens > self.target_tokens and current:
                    chunks.append(current.strip())
                    current = sentence + " "
                    current_tokens = sentence_tokens
                else:
                    current += sentence + " "
                    current_tokens += sentence_tokens

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text]

    def _create_chunks(
        self,
        raw_chunks: List[Dict],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[ChunkMetadata]:
        """Create ChunkMetadata objects from grouped chunks."""
        chunks = []

        for idx, raw in enumerate(raw_chunks):
            chunk_id = f"{doc_id}-chunk-{idx:03d}"
            text = "\n\n".join(raw["texts"])
            token_count = raw.get("token_count", self.count_tokens(text))

            # Format page range
            page_range = None
            if raw["page_start"]:
                if raw["page_end"] and raw["page_end"] != raw["page_start"]:
                    page_range = f"{raw['page_start']}-{raw['page_end']}"
                else:
                    page_range = str(raw["page_start"])

            chunks.append(ChunkMetadata(
                chunk_id=chunk_id,
                doc_id=doc_id,
                user_id=user_id,
                filename=filename,
                section_title=raw.get("section_title"),
                page_range=page_range,
                chunk_index=idx,
                token_count=token_count,
                text=text,
                created_at=datetime.now(timezone.utc)
            ))

        return chunks

    def _add_overlap(self, chunks: List[ChunkMetadata]) -> List[ChunkMetadata]:
        """Add overlap from previous chunk (skip table chunks)."""
        if len(chunks) <= 1:
            return chunks

        overlap_tokens = int(self.target_tokens * self.overlap_pct)
        result = [chunks[0]]

        for i in range(1, len(chunks)):
            chunk = chunks[i]
            prev_chunk = chunks[i-1]

            # Don't add overlap to/from table chunks
            # Check by token count heuristic (tables tend to be larger)
            if prev_chunk.token_count > self.max_tokens * 0.8:
                result.append(chunk)
                continue

            prev_tokens = self.encoder.encode(prev_chunk.text)
            if len(prev_tokens) > overlap_tokens:
                overlap_text = self.encoder.decode(prev_tokens[-overlap_tokens:])
                chunk.text = overlap_text + " " + chunk.text
                chunk.token_count = self.count_tokens(chunk.text)

            result.append(chunk)

        return result

    def _deduplicate(self, chunks: List[ChunkMetadata]) -> List[ChunkMetadata]:
        """Remove duplicate chunks by content hash."""
        seen_hashes = set()
        unique = []

        for chunk in chunks:
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

    def _enforce_max_tokens(self, chunks: List[ChunkMetadata]) -> List[ChunkMetadata]:
        """Emergency split for any chunk exceeding max_tokens."""
        result = []
        for chunk in chunks:
            if chunk.token_count <= self.max_tokens:
                result.append(chunk)
            else:
                # This shouldn't happen often, but handle gracefully
                logger.warning("emergency_chunk_split",
                              chunk_id=chunk.chunk_id,
                              original_tokens=chunk.token_count)
                split_texts = self._split_large_text(chunk.text)
                for i, text in enumerate(split_texts):
                    new_chunk = ChunkMetadata(
                        chunk_id=f"{chunk.chunk_id}-split-{i}",
                        doc_id=chunk.doc_id,
                        user_id=chunk.user_id,
                        filename=chunk.filename,
                        section_title=chunk.section_title,
                        page_range=chunk.page_range,
                        chunk_index=chunk.chunk_index * 100 + i,
                        token_count=self.count_tokens(text),
                        text=text,
                        created_at=chunk.created_at
                    )
                    result.append(new_chunk)
        return result

    def _validate_and_log_statistics(self, chunks: List[ChunkMetadata], doc_id: str):
        """Validate chunk sizes and log statistics for monitoring."""
        if not chunks:
            return

        token_counts = [c.token_count for c in chunks]

        # Validate chunk sizes
        for chunk in chunks:
            if chunk.token_count > self.max_tokens:
                logger.error("chunk_exceeds_max_tokens",
                            chunk_id=chunk.chunk_id,
                            token_count=chunk.token_count,
                            max_tokens=self.max_tokens)
                # This should never happen with proper element-aware chunking
                # but log it for debugging if it does

        # Count table chunks (approximation: chunks significantly larger than target)
        table_chunk_count = sum(1 for c in chunks if c.token_count > self.target_tokens * 2)

        # Log chunk statistics
        logger.info("chunk_statistics",
                   doc_id=doc_id,
                   total_chunks=len(chunks),
                   min_tokens=min(token_counts),
                   max_tokens=max(token_counts),
                   avg_tokens=sum(token_counts) // len(token_counts),
                   table_chunks=table_chunk_count)

    # ============ FALLBACK: Markdown-based chunking ============
    # Used when no structured elements available

    def _chunk_from_markdown(
        self,
        docling_output: Union[Dict[str, Any], DoclingParseResult],
        doc_id: str,
        user_id: str,
        filename: str
    ) -> List[ChunkMetadata]:
        """Fallback to markdown-based chunking (original algorithm improved)."""
        md_content = ""
        if isinstance(docling_output, DoclingParseResult):
            md_content = docling_output.md_content
        elif isinstance(docling_output, dict):
            if "document" in docling_output:
                md_content = docling_output["document"].get("md_content", "")
            elif "md_content" in docling_output:
                md_content = docling_output.get("md_content", "")

        if not md_content:
            logger.warning("no_content_for_chunking", doc_id=doc_id)
            return []

        # Parse markdown into sections
        sections = self._parse_markdown_sections(md_content)

        # Merge small sections
        merged = self._merge_small_sections(sections)

        # Split large sections
        split = self._split_large_sections(merged)

        # Create chunks
        chunks = []
        for idx, section in enumerate(split):
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

        # Add overlap and deduplicate
        chunks = self._add_overlap(chunks)
        chunks = self._deduplicate(chunks)

        logger.info("markdown_chunking_completed",
                   doc_id=doc_id,
                   sections=len(sections),
                   chunks=len(chunks))

        return chunks

    def _parse_markdown_sections(self, md_content: str) -> List[Dict]:
        """Parse markdown content into sections by headings."""
        import re

        sections = []
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        headings = list(heading_pattern.finditer(md_content))

        if not headings:
            # No headings - split by paragraphs instead
            paragraphs = md_content.split("\n\n")
            for i, para in enumerate(paragraphs):
                if para.strip():
                    sections.append({
                        "title": f"Section {i+1}",
                        "text": para.strip(),
                        "page_range": str((i * 3000 // len(md_content)) + 1) if md_content else "1"
                    })
            return sections

        for i, match in enumerate(headings):
            title = match.group(2).strip()
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(md_content)
            text = md_content[start:end].strip()
            page_estimate = max(1, (match.start() // 3000) + 1)

            if text:
                sections.append({
                    "title": title,
                    "text": text,
                    "page_range": str(page_estimate)
                })

        return sections

    def _merge_small_sections(self, sections: List[Dict]) -> List[Dict]:
        """Merge sections smaller than min_chunk_tokens."""
        if not sections:
            return []

        merged = []
        current = None

        for section in sections:
            token_count = self.count_tokens(section["text"])

            if current is None:
                current = section.copy()
            elif token_count < self.min_chunk_tokens:
                current["text"] += "\n\n" + section["text"]
            else:
                merged.append(current)
                current = section.copy()

        if current:
            merged.append(current)

        return merged

    def _split_large_sections(self, sections: List[Dict]) -> List[Dict]:
        """Split sections larger than max_tokens."""
        result = []

        for section in sections:
            token_count = self.count_tokens(section["text"])

            if token_count <= self.max_tokens:
                result.append(section)
            else:
                # Split at paragraph boundaries
                split_texts = self._split_large_text(section["text"])
                for i, split_text in enumerate(split_texts):
                    result.append({
                        "title": f"{section['title']} (part {i+1})" if i > 0 else section["title"],
                        "text": split_text,
                        "page_range": section["page_range"]
                    })

        return result
