"""Async client for docling-serve API with retry logic."""
import backoff
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.logging import get_logger
from app.config import settings

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
    async def parse_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse document via docling-serve with retry on transient failures.

        Returns docling output with sections, headings, tables structure.
        Raises DoclingParseError on permanent failure.
        """
        logger.info("docling_parse_started", file_path=str(file_path))

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, 'rb') as f:
                content_type = self._get_content_type(file_path)
                files = {'file': (file_path.name, f, content_type)}

                try:
                    response = await client.post(
                        f"{self.base_url}/v1/convert/file",
                        files=files,
                        params={
                            "to_formats": "json",
                            "do_ocr": "true"
                        }
                    )
                    response.raise_for_status()

                    result = response.json()
                    logger.info("docling_parse_completed",
                               sections=len(result.get("sections", [])))
                    return result

                except httpx.HTTPStatusError as e:
                    if e.response.status_code < 500:
                        # Permanent error (4xx)
                        logger.error("docling_parse_failed",
                                   status_code=e.response.status_code,
                                   response=e.response.text[:500])
                        raise DoclingParseError(f"Docling parse failed: {e.response.status_code}")
                    raise  # Let backoff handle 5xx

    def _get_content_type(self, file_path: Path) -> str:
        """Get MIME type from file extension."""
        ext = file_path.suffix.lower()
        return {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }.get(ext, 'application/octet-stream')
