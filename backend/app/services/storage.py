"""Secure file storage service with path validation."""
import re
import shutil
from pathlib import Path
from typing import Dict
import aiofiles
import structlog

logger = structlog.get_logger(__name__)


class StorageService:
    """Secure file storage with path traversal protection."""

    def __init__(self, base_path: str):
        """Initialize storage service.

        Args:
            base_path: Base directory for all file storage
        """
        self.base_path = Path(base_path).resolve()
        self._ensure_base_dir()
        logger.info("storage_service_initialized", base_path=str(self.base_path))

    def _ensure_base_dir(self) -> None:
        """Ensure base storage directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks.

        Removes path components and keeps only safe characters:
        - Alphanumeric
        - Dots, hyphens, underscores
        - Limited to 255 characters

        Args:
            filename: Original filename

        Returns:
            Sanitized filename with unsafe characters replaced

        Examples:
            >>> s = StorageService("/tmp/test")
            >>> s.sanitize_filename("../../../etc/passwd")
            '___etc_passwd'
            >>> s.sanitize_filename("my file.pdf")
            'my_file.pdf'
        """
        # Remove any directory components
        filename = Path(filename).name

        # Replace unsafe characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Limit length to 255 characters
        if len(sanitized) > 255:
            # Preserve extension if possible
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            max_name_len = 255 - len(ext) - 1 if ext else 255
            sanitized = f"{name[:max_name_len]}.{ext}" if ext else name[:255]

        # Ensure not empty
        if not sanitized or sanitized == '.':
            sanitized = 'unnamed_file'

        logger.debug(
            "filename_sanitized",
            original=filename,
            sanitized=sanitized,
        )

        return sanitized

    def validate_path(self, path: Path, base: Path) -> bool:
        """Validate path is within base directory.

        Uses path.resolve() to expand symlinks and relative paths,
        then checks if resolved path is relative to base.

        Args:
            path: Path to validate
            base: Base directory that path must be within

        Returns:
            True if path is within base directory

        Raises:
            ValueError: If path traversal attempt detected
        """
        try:
            resolved_path = path.resolve()
            resolved_base = base.resolve()

            is_valid = resolved_path.is_relative_to(resolved_base)

            if not is_valid:
                logger.error(
                    "path_traversal_attempt",
                    requested_path=str(path),
                    resolved_path=str(resolved_path),
                    base_path=str(resolved_base),
                )
                raise ValueError(
                    f"Path traversal detected: {path} is not relative to {base}"
                )

            return True

        except (ValueError, OSError) as e:
            logger.error(
                "path_validation_failed",
                path=str(path),
                base=str(base),
                error=str(e),
            )
            raise ValueError(f"Invalid path: {path}") from e

    def get_raw_path(self, user_id: str, doc_id: str, filename: str) -> Path:
        """Get validated path for raw uploaded file.

        Args:
            user_id: User identifier
            doc_id: Document identifier
            filename: Original filename (will be sanitized)

        Returns:
            Validated Path object

        Raises:
            ValueError: If path validation fails
        """
        sanitized_filename = self.sanitize_filename(filename)
        path = self.base_path / "raw" / user_id / doc_id / sanitized_filename

        # Validate before returning
        self.validate_path(path, self.base_path)

        return path

    def get_processed_path(self, user_id: str, doc_id: str) -> Path:
        """Get validated path for processed document directory.

        Args:
            user_id: User identifier
            doc_id: Document identifier

        Returns:
            Validated Path object for processed files directory

        Raises:
            ValueError: If path validation fails
        """
        path = self.base_path / "processed" / user_id / doc_id

        # Validate before returning
        self.validate_path(path, self.base_path)

        return path

    async def save_upload(
        self,
        user_id: str,
        doc_id: str,
        filename: str,
        content: bytes
    ) -> Path:
        """Save uploaded file to storage.

        Args:
            user_id: User identifier
            doc_id: Document identifier
            filename: Original filename
            content: File content as bytes

        Returns:
            Path where file was saved

        Raises:
            ValueError: If path validation fails
            OSError: If file write fails
        """
        file_path = self.get_raw_path(user_id, doc_id, filename)

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file asynchronously
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        logger.info(
            "file_uploaded",
            user_id=user_id,
            doc_id=doc_id,
            filename=filename,
            path=str(file_path),
            size_bytes=len(content),
        )

        return file_path

    async def save_processed_json(
        self,
        user_id: str,
        doc_id: str,
        data: Dict
    ) -> Path:
        """Save processed document data as JSON.

        Args:
            user_id: User identifier
            doc_id: Document identifier
            data: Document data to save as JSON

        Returns:
            Path where JSON was saved

        Raises:
            ValueError: If path validation fails
            OSError: If file write fails
        """
        import json

        dir_path = self.get_processed_path(user_id, doc_id)
        file_path = dir_path / "docling_output.json"

        # Create parent directories
        dir_path.mkdir(parents=True, exist_ok=True)

        # Write JSON asynchronously
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2))

        logger.info(
            "processed_json_saved",
            user_id=user_id,
            doc_id=doc_id,
            path=str(file_path),
        )

        return file_path

    def delete_document_files(self, user_id: str, doc_id: str) -> None:
        """Delete all files for a document (raw and processed).

        Args:
            user_id: User identifier
            doc_id: Document identifier
        """
        raw_path = self.base_path / "raw" / user_id / doc_id
        processed_path = self.base_path / "processed" / user_id / doc_id

        deleted_paths = []

        # Delete raw files
        if raw_path.exists():
            shutil.rmtree(raw_path, ignore_errors=True)
            deleted_paths.append(str(raw_path))

        # Delete processed files
        if processed_path.exists():
            shutil.rmtree(processed_path, ignore_errors=True)
            deleted_paths.append(str(processed_path))

        if deleted_paths:
            logger.info(
                "document_files_deleted",
                user_id=user_id,
                doc_id=doc_id,
                paths=deleted_paths,
            )
        else:
            logger.debug(
                "no_files_to_delete",
                user_id=user_id,
                doc_id=doc_id,
            )
