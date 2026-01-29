"""Async client for docling-serve API with retry logic."""
import backoff
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.core.logging import get_logger
from app.config import settings
from app.models.documents import (
    DoclingParseResult,
    DoclingElement,
    DoclingTextElement,
    DoclingTableElement,
    DoclingHeadingElement,
    DoclingListItemElement,
)

logger = get_logger()


class DoclingError(Exception):
    """Base exception for docling client errors."""
    pass


class DoclingParseError(DoclingError):
    """Raised when document parsing fails."""
    pass


class DoclingClient:
    """Async client for docling-serve API with retry logic."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 120.0):
        self.base_url = base_url or settings.DOCLING_URL
        self.timeout = timeout

    def _is_transient_error(self, exception: Exception) -> bool:
        """Determine if error is transient and should be retried."""
        if isinstance(exception, httpx.TimeoutException):
            return True
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code >= 500
        return False

    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.NetworkError),
        max_tries=3,
        max_time=180,
        on_backoff=lambda details: logger.warning(
            "docling_retry",
            attempt=details["tries"],
            wait=details["wait"]
        )
    )
    async def parse_document(self, file_path: Path) -> DoclingParseResult:
        """
        Parse document via docling-serve with retry on transient failures.

        Returns DoclingParseResult with structured elements and markdown fallback.
        Raises DoclingParseError on permanent failure.
        """
        logger.info("docling_parse_started", file_path=str(file_path))

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, 'rb') as f:
                content_type = self._get_content_type(file_path)
                files = {'files': (file_path.name, f, content_type)}

                try:
                    response = await client.post(
                        f"{self.base_url}/v1/convert/file",
                        files=files,
                        params={
                            "to_formats": "json,md",  # Request both JSON and Markdown
                            "do_ocr": "true"
                        }
                    )
                    response.raise_for_status()

                    result = response.json()
                    document = result.get("document", result)  # Handle both nested and flat response

                    # Extract structured elements from json_content
                    json_content = document.get("json_content", {}) or {}
                    elements = self._extract_elements(json_content) if json_content else []

                    # Get markdown as fallback
                    md_content = document.get("md_content", "") or ""

                    # Get page count from various possible locations
                    page_count = (
                        json_content.get("page_count", 0) or
                        len(json_content.get("pages", [])) or
                        document.get("page_count", 0) or
                        len(document.get("pages", []))
                    )

                    logger.info("docling_parse_completed",
                               elements=len(elements),
                               page_count=page_count,
                               has_md_content=bool(md_content))

                    return DoclingParseResult(
                        elements=elements,
                        md_content=md_content,
                        page_count=page_count,
                        raw_json=None  # Set to json_content for debugging if needed
                    )

                except httpx.HTTPStatusError as e:
                    if e.response.status_code < 500:
                        # Permanent error (4xx)
                        logger.error("docling_parse_failed",
                                   status_code=e.response.status_code,
                                   response=e.response.text[:500])
                        raise DoclingParseError(f"Docling parse failed: {e.response.status_code}")
                    raise  # Let backoff handle 5xx

    def _extract_elements(self, json_content: dict) -> List[DoclingElement]:
        """
        Extract typed elements from DoclingDocument json_content.

        Handles the DoclingDocument structure with body tree, texts array, and tables array.
        Returns elements in reading order based on document hierarchy.
        """
        elements: List[DoclingElement] = []

        # DoclingDocument structure has multiple possible layouts
        # Layout 1: body tree with $ref pointers to texts/tables arrays
        body = json_content.get("body", {})
        texts = json_content.get("texts", [])
        tables = json_content.get("tables", [])

        if body and (texts or tables):
            # Traverse body tree to extract elements in reading order
            self._traverse_body(body, texts, tables, elements, level=0)
        else:
            # Layout 2: Direct items/elements array (alternative docling format)
            items = json_content.get("items", json_content.get("elements", []))
            for item in items:
                element = self._parse_item(item)
                if element:
                    elements.append(element)

        # If no elements extracted but we have texts/tables directly, extract them
        if not elements:
            for idx, text_item in enumerate(texts):
                element = self._text_item_to_element(text_item, level=0)
                if element:
                    elements.append(element)
            for idx, table_item in enumerate(tables):
                element = self._table_item_to_element(table_item, level=0)
                if element:
                    elements.append(element)

        return elements

    def _traverse_body(
        self,
        node: dict,
        texts: list,
        tables: list,
        elements: list,
        level: int
    ):
        """Recursively traverse body tree to build element list in reading order."""
        children = node.get("children", [])

        for child in children:
            ref = child.get("$ref", "")

            # Resolve reference to actual content
            if "/texts/" in ref:
                try:
                    idx = int(ref.split("/texts/")[1].split("/")[0])
                    if idx < len(texts):
                        element = self._text_item_to_element(texts[idx], level)
                        if element:
                            elements.append(element)
                except (ValueError, IndexError):
                    pass

            elif "/tables/" in ref:
                try:
                    idx = int(ref.split("/tables/")[1].split("/")[0])
                    if idx < len(tables):
                        element = self._table_item_to_element(tables[idx], level)
                        if element:
                            elements.append(element)
                except (ValueError, IndexError):
                    pass

            # Recurse into nested children
            if "children" in child:
                self._traverse_body(child, texts, tables, elements, level + 1)

    def _text_item_to_element(self, text_item: dict, level: int) -> Optional[DoclingElement]:
        """Convert a text item to the appropriate DoclingElement type."""
        text = text_item.get("text", "").strip()
        if not text:
            return None

        label = text_item.get("label", "").lower()
        page_number = self._get_page_number(text_item)

        # Determine element type based on label
        if label in ("section_header", "title", "heading"):
            heading_level = text_item.get("heading_level", text_item.get("level", 1))
            return DoclingHeadingElement(
                text=text,
                page_number=page_number,
                level=level,
                heading_level=heading_level
            )
        elif label in ("list_item", "list-item"):
            marker = text_item.get("marker", text_item.get("enumeration", None))
            return DoclingListItemElement(
                text=text,
                page_number=page_number,
                level=level,
                marker=marker
            )
        else:
            # Default to text element (paragraph, caption, etc.)
            return DoclingTextElement(
                text=text,
                page_number=page_number,
                level=level,
                label=label or "paragraph"
            )

    def _table_item_to_element(self, table_item: dict, level: int) -> Optional[DoclingElement]:
        """Convert a table item to DoclingTableElement."""
        # Export table as markdown for text representation
        table_md = self._table_to_markdown(table_item)
        if not table_md:
            return None

        page_number = self._get_page_number(table_item)
        data = table_item.get("data", {})

        return DoclingTableElement(
            text=table_md,
            page_number=page_number,
            level=level,
            num_rows=data.get("num_rows"),
            num_cols=data.get("num_cols"),
            is_atomic=True  # Tables should never be split
        )

    def _parse_item(self, item: dict) -> Optional[DoclingElement]:
        """Parse a generic item from items/elements array."""
        item_type = item.get("type", item.get("element_type", "")).lower()
        text = item.get("text", item.get("content", "")).strip()
        if not text:
            return None

        page_number = self._get_page_number(item)
        level = item.get("level", 0)

        if item_type in ("table",):
            return DoclingTableElement(
                text=text,
                page_number=page_number,
                level=level,
                num_rows=item.get("num_rows"),
                num_cols=item.get("num_cols"),
                is_atomic=True
            )
        elif item_type in ("heading", "section_header", "title"):
            return DoclingHeadingElement(
                text=text,
                page_number=page_number,
                level=level,
                heading_level=item.get("heading_level", 1)
            )
        elif item_type in ("list_item", "list-item"):
            return DoclingListItemElement(
                text=text,
                page_number=page_number,
                level=level,
                marker=item.get("marker")
            )
        else:
            return DoclingTextElement(
                text=text,
                page_number=page_number,
                level=level,
                label=item_type or "paragraph"
            )

    def _get_page_number(self, item: dict) -> Optional[int]:
        """Extract page number from item's prov or page fields."""
        # Try prov (provenance) field first
        prov = item.get("prov", [])
        if prov and isinstance(prov, list) and len(prov) > 0:
            page = prov[0].get("page", prov[0].get("page_no"))
            if page is not None:
                return int(page) + 1  # Convert 0-indexed to 1-indexed

        # Try direct page fields
        for field in ("page", "page_number", "page_no"):
            page = item.get(field)
            if page is not None:
                # Handle 0-indexed vs 1-indexed
                return int(page) if int(page) > 0 else int(page) + 1

        return None

    def _table_to_markdown(self, table_item: dict) -> str:
        """Convert table item to markdown string representation."""
        # Check for pre-formatted markdown
        if "markdown" in table_item:
            return table_item["markdown"]
        if "md" in table_item:
            return table_item["md"]

        # Build markdown from data structure
        data = table_item.get("data", {})
        grid = data.get("grid", data.get("cells", []))

        if not grid:
            # Fallback to text content if available
            return table_item.get("text", "")

        # Build markdown table
        lines = []
        for row_idx, row in enumerate(grid):
            cells = []
            for cell in row:
                if isinstance(cell, dict):
                    cell_text = cell.get("text", cell.get("value", ""))
                else:
                    cell_text = str(cell) if cell else ""
                cells.append(cell_text.replace("|", "\\|").replace("\n", " "))
            lines.append("| " + " | ".join(cells) + " |")

            # Add header separator after first row
            if row_idx == 0:
                separator = "| " + " | ".join(["---"] * len(cells)) + " |"
                lines.append(separator)

        return "\n".join(lines)

    def _get_content_type(self, file_path: Path) -> str:
        """Get MIME type from file extension."""
        ext = file_path.suffix.lower()
        return {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }.get(ext, 'application/octet-stream')
