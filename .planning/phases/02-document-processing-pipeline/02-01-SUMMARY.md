---
phase: 02-document-processing-pipeline
plan: 01
subsystem: database
tags: [pydantic, aiosqlite, storage, file-handling, security]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: "Configuration patterns (pydantic-settings), logging (structlog), async patterns"
provides:
  - "Document data models with processing status tracking"
  - "Async SQLite database layer for document metadata"
  - "Secure file storage service with path traversal protection"
  - "Document processing state machine (Uploading → Parsing → Chunking → Indexing → Done/Failed)"
affects: [02-02-upload-api, 02-03-docling-integration, 03-rag-pipeline]

# Tech tracking
tech-stack:
  added: [aiosqlite, aiofiles, tiktoken, httpx, backoff]
  patterns:
    - "Pydantic models for document metadata and chunks"
    - "Async SQLite with WAL mode for concurrency"
    - "Path sanitization with resolve() and is_relative_to() validation"
    - "Processing log as JSON-serialized list in SQLite"

key-files:
  created:
    - backend/app/models/documents.py
    - backend/app/models/__init__.py
    - backend/app/core/database.py
    - backend/app/services/storage.py
    - backend/app/services/__init__.py
  modified:
    - backend/app/config.py
    - backend/requirements.txt

key-decisions:
  - "ProcessingStatus enum with 6 states for detailed pipeline tracking"
  - "Store processing_log as JSON in SQLite (simple, queryable, preserves structure)"
  - "Path validation uses resolve() + is_relative_to() for security (RESEARCH.md pitfall #2)"
  - "Sanitize filenames with regex [^a-zA-Z0-9._-] replacement"
  - "Directory structure: /data/{raw,processed}/{user_id}/{doc_id}/"

patterns-established:
  - "Document model: Complete metadata including timestamps, status, page/chunk counts"
  - "ChunkMetadata model: doc_id-chunk-NNN format for human-readable IDs"
  - "StorageService: All file operations go through validated paths"
  - "Async file operations with aiofiles throughout"

# Metrics
duration: 5min
completed: 2026-01-27
---

# Phase 02 Plan 01: Document Storage Foundation Summary

**Document models with 6-stage processing state machine, async SQLite tracking, and path-traversal-protected file storage**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-27T21:45:38Z
- **Completed:** 2026-01-27T21:50:50Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Document, ProcessingStatus, ChunkMetadata, and ProcessingLogEntry models define complete schema for document processing pipeline
- DocumentDatabase provides async CRUD operations with WAL mode for concurrent access
- StorageService prevents path traversal attacks through filename sanitization and path validation
- Configuration extended with DATA_DIR, DOCLING_URL, MAX_FILE_SIZE_MB, MAX_DOCUMENTS_PER_USER settings

## Task Commits

Each task was committed atomically:

1. **Task 1: Create document models and database schema** - `7272e4b` (feat)
2. **Task 2: Create secure file storage service** - `38d39a4` (feat)

## Files Created/Modified

**Created:**
- `backend/app/models/documents.py` - Document, ProcessingStatus, ChunkMetadata, ProcessingLogEntry Pydantic models
- `backend/app/models/__init__.py` - Model exports
- `backend/app/core/database.py` - DocumentDatabase with async SQLite operations (create, get, update, list, delete)
- `backend/app/services/storage.py` - StorageService with path validation and sanitization
- `backend/app/services/__init__.py` - Service exports

**Modified:**
- `backend/app/config.py` - Added DATA_DIR, DOCLING_URL, MAX_FILE_SIZE_MB, MAX_DOCUMENTS_PER_USER, database_path property
- `backend/requirements.txt` - Added aiosqlite, aiofiles, tiktoken, httpx, backoff

## Decisions Made

1. **ProcessingStatus enum with 6 states:** UPLOADING, PARSING, CHUNKING, INDEXING, DONE, FAILED - provides granular visibility into pipeline progress (supports Phase 2 CONTEXT.md requirement for detailed status tracking)

2. **Processing log as JSON in SQLite:** Storing List[ProcessingLogEntry] as JSON string enables flexible stage tracking without complex schema changes. Easy to query and expand for debugging.

3. **Path security via resolve() + is_relative_to():** Following RESEARCH.md pitfall #2, all paths are resolved to absolute form and validated against base directory before any file operation. Prevents symlink and relative path attacks.

4. **Filename sanitization with regex:** Replace all characters except [a-zA-Z0-9._-] with underscores, strip directory components via Path(filename).name. 255-character limit with extension preservation.

5. **Directory structure /data/{raw,processed}/{user_id}/{doc_id}/:** Clear separation between uploaded files (raw) and docling output (processed). User and document isolation built into path structure.

6. **WAL mode for SQLite:** Enables concurrent reads during document processing without blocking. Essential for polling status updates while processing runs.

7. **ChunkMetadata format doc_id-chunk-NNN:** Human-readable chunk IDs simplify debugging and log analysis. Three-digit zero-padding supports up to 999 chunks per document.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - straightforward implementation with clear requirements from plan and CONTEXT.md.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 02-02 (Upload API):**
- Document model ready for status tracking during upload
- StorageService.save_upload() ready for multipart file handling
- DocumentDatabase.create_document() ready for initial document records
- Configuration includes MAX_FILE_SIZE_MB (10MB) and MAX_DOCUMENTS_PER_USER (10) for validation

**Ready for Plan 02-03 (Docling Integration):**
- StorageService.get_raw_path() provides paths for sending to docling-serve
- StorageService.save_processed_json() ready for docling output storage
- Processing log structure supports timestamp tracking per stage
- Status transitions defined (Parsing → Chunking → Indexing)

**No blockers.** All foundation pieces in place for document upload and processing.

---
*Phase: 02-document-processing-pipeline*
*Completed: 2026-01-27*
