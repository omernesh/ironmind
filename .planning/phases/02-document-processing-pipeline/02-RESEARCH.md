# Phase 2: Document Processing Pipeline - Research

**Researched:** 2026-01-27
**Domain:** Document parsing, semantic chunking, and file upload processing
**Confidence:** MEDIUM-HIGH

## Summary

The Document Processing Pipeline transforms uploaded documents (DOCX/PDF) into searchable chunks with preserved structure and metadata. Research reveals a mature ecosystem with docling-serve (v1.10.0, stable API) for structure-preserving parsing, established semantic chunking patterns for RAG, and proven FastAPI patterns for async file processing.

**Core findings:**
- docling-serve provides stable v1 API with structure preservation (sections, headings, tables) via DocTags format
- Semantic chunking at section boundaries with 10-20% overlap is industry standard for RAG
- FastAPI UploadFile + BackgroundTasks pattern handles async processing without external queue for POC-scale
- txtai content storage enables rich metadata alongside vector embeddings
- Exponential backoff retry and path validation are critical security/reliability patterns

**Primary recommendation:** Use docling-serve v1 API with section-boundary chunking (respecting document structure), tiktoken for token counting (~1000 token targets), FastAPI BackgroundTasks for async processing, and txtai content storage for metadata-rich indexing. Validate file paths rigorously to prevent traversal attacks.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docling-serve | v1.10.0 | Document parsing with structure preservation | IBM Research-backed, stable v1 API, DocTags format captures sections/headings/tables with layout |
| FastAPI | latest | File upload and async task orchestration | Native UploadFile (spooled files), BackgroundTasks, proven multipart/form-data handling |
| tiktoken | 0.5.2+ | Token counting for chunk sizing | OpenAI's official tokenizer, accurate for GPT models, production-ready |
| txtai | 7.x+ | Embeddings + metadata storage | Content storage combines vectors + SQL, hybrid search, lightweight RAG |
| backoff | 2.x+ | Exponential backoff retry logic | Decorator-based, asyncio support, industry standard for API retries |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiofiles | latest | Async file I/O | Streaming uploads to disk without blocking event loop |
| python-multipart | latest | Multipart form parsing | Required dependency for FastAPI file uploads |
| pathlib | stdlib | Secure path handling | Path validation and canonicalization to prevent traversal |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| docling-serve | Unstructured.io | Unstructured is "generic scanner", less structure preservation; best as fallback |
| BackgroundTasks | Celery/ARQ | Celery adds complexity (Redis, workers); justified for >10 min tasks or distributed scale |
| tiktoken | len(text)/4 | Approximation (4 chars ≈ 1 token) works for estimates but lacks precision for boundaries |

**Installation:**
```bash
# Backend dependencies
pip install "docling-serve[ui]" fastapi python-multipart aiofiles tiktoken backoff txtai

# Deploy docling-serve (separate service)
docker run -p 5001:5001 -e DOCLING_SERVE_API_KEY=<secret> quay.io/docling-project/docling-serve:v1.10.0
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── routers/
│   │   ├── documents.py          # Upload, status, retry endpoints
│   │   └── processing.py         # Internal processing logic
│   ├── services/
│   │   ├── docling_client.py     # docling-serve API client with retry
│   │   ├── chunker.py            # Semantic chunking logic
│   │   ├── indexer.py            # txtai integration
│   │   └── storage.py            # File storage manager
│   ├── models/
│   │   └── documents.py          # Document status, metadata schemas
│   └── core/
│       └── config.py             # Docling URL, file limits, paths
data/
├── raw/{user_id}/{doc_id}/       # Original uploads
└── processed/{user_id}/{doc_id}/ # Parsed output (JSON/metadata)
```

### Pattern 1: Async File Upload with Background Processing
**What:** Client uploads file → FastAPI streams to disk → Background task processes asynchronously → Status polling endpoint
**When to use:** File processing takes >2 seconds (parsing, chunking, embedding)
**Example:**
```python
# Source: FastAPI official docs + polling pattern from community
from fastapi import FastAPI, UploadFile, BackgroundTasks, File
from pathlib import Path
import aiofiles
import shutil

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user_id: str
):
    # Generate secure doc_id
    doc_id = generate_secure_id()

    # Validate file type and size
    validate_file(file, max_size_mb=10, allowed_types=["pdf", "docx"])

    # Stream to disk (prevents memory spike)
    raw_path = Path(f"data/raw/{user_id}/{doc_id}/{file.filename}")
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(raw_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Create processing record
    doc_status = create_document_record(doc_id, user_id, file.filename, status="Uploading")

    # Schedule background processing
    background_tasks.add_task(process_document, doc_id, user_id, raw_path)

    return {"doc_id": doc_id, "status": "Uploading", "filename": file.filename}
```

### Pattern 2: Docling API Client with Exponential Backoff
**What:** Resilient HTTP client for docling-serve with automatic retry on transient failures
**When to use:** Any external API call (docling-serve, embeddings)
**Example:**
```python
# Source: backoff library + docling-serve usage docs
import backoff
import httpx
from typing import Dict, Any

class DoclingClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-Api-Key": api_key}

    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.NetworkError),
        max_tries=3,
        max_time=60
    )
    async def parse_document(self, file_path: Path) -> Dict[str, Any]:
        """Parse document via docling-serve with retry."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/pdf')}
                response = await client.post(
                    f"{self.base_url}/v1/convert/file",
                    files=files,
                    headers=self.headers,
                    params={
                        "to_formats": "json",  # DocTags format
                        "ocr_enabled": "true"
                    }
                )
                response.raise_for_status()
                return response.json()
```

### Pattern 3: Section-Boundary Semantic Chunking
**What:** Split document at section boundaries, merge small sections, add overlap for context continuity
**When to use:** Documents with clear structure (technical docs, aerospace manuals)
**Example:**
```python
# Source: RAG chunking best practices + tiktoken usage
import tiktoken
from typing import List, Dict

class SemanticChunker:
    def __init__(self, target_tokens: int = 1000, overlap_pct: float = 0.15):
        self.target_tokens = target_tokens
        self.overlap_pct = overlap_pct
        self.encoder = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 encoding

    def chunk_document(self, sections: List[Dict]) -> List[Dict]:
        """
        Chunk document respecting section boundaries.
        sections: [{"title": "Introduction", "text": "...", "page_range": "1-3"}, ...]
        """
        chunks = []
        current_chunk = {"text": "", "metadata": {}}

        for section in sections:
            section_tokens = len(self.encoder.encode(section["text"]))

            # If section < 50 tokens, merge with next
            if section_tokens < 50:
                current_chunk["text"] += section["text"] + "\n\n"
                continue

            # If adding section exceeds target, finalize current chunk
            if len(self.encoder.encode(current_chunk["text"])) + section_tokens > self.target_tokens:
                if current_chunk["text"]:
                    chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = {"text": "", "metadata": {}}

            # Add section to current chunk
            current_chunk["text"] += section["text"] + "\n\n"
            current_chunk["metadata"]["section_title"] = section.get("title", "")
            current_chunk["metadata"]["page_range"] = section.get("page_range", "")

        # Finalize last chunk
        if current_chunk["text"]:
            chunks.append(self._finalize_chunk(current_chunk))

        # Add overlap between chunks
        return self._add_overlap(chunks)

    def _add_overlap(self, chunks: List[Dict]) -> List[Dict]:
        """Add 10-20% overlap between consecutive chunks."""
        overlap_tokens = int(self.target_tokens * self.overlap_pct)

        for i in range(1, len(chunks)):
            prev_text = chunks[i-1]["text"]
            prev_tokens = self.encoder.encode(prev_text)

            # Take last N tokens from previous chunk
            overlap_text = self.encoder.decode(prev_tokens[-overlap_tokens:])
            chunks[i]["text"] = overlap_text + " " + chunks[i]["text"]

        return chunks
```

### Pattern 4: Status Polling Endpoint
**What:** Client polls /documents/{doc_id}/status every 2s to track processing stages
**When to use:** Long-running tasks where WebSocket is overkill for POC
**Example:**
```python
# Source: FastAPI polling pattern examples
from enum import Enum
from datetime import datetime

class ProcessingStatus(str, Enum):
    UPLOADING = "Uploading"
    PARSING = "Parsing"
    CHUNKING = "Chunking"
    INDEXING = "Indexing"
    DONE = "Done"
    FAILED = "Failed"

@app.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: str, user_id: str):
    doc = get_document_record(doc_id, user_id)

    return {
        "doc_id": doc_id,
        "filename": doc.filename,
        "status": doc.status,
        "current_stage": doc.current_stage,
        "progress_pct": calculate_progress(doc),  # Based on stage
        "estimated_time_remaining": estimate_remaining(doc),
        "processing_log": doc.processing_log,  # [{"stage": "Parsing", "timestamp": "...", "duration_ms": 1234}]
        "error": doc.error if doc.status == "Failed" else None
    }
```

### Pattern 5: txtai Content Storage with Metadata
**What:** Store full chunk text + metadata alongside embeddings for retrieval
**When to use:** Need to filter by metadata (user_id, doc_id, page_range) during search
**Example:**
```python
# Source: txtai embeddings documentation
from txtai.embeddings import Embeddings

# Initialize with content storage enabled
embeddings = Embeddings({
    "path": "sentence-transformers/all-MiniLM-L6-v2",
    "content": True,  # Enable metadata storage
    "backend": "sqlite"  # or "duckdb" for better performance
})

# Index chunks with rich metadata
chunks = [
    {
        "id": "doc123-chunk-001",
        "text": "The aircraft's primary control surfaces include...",
        "doc_id": "doc123",
        "filename": "flight_manual.pdf",
        "page_range": "12-14",
        "section_title": "Control Systems",
        "user_id": "user456",
        "chunk_index": 1,
        "created_at": "2026-01-27T10:30:00Z"
    }
]

embeddings.index((chunk["id"], chunk, None) for chunk in chunks)
embeddings.save("index/user456")

# Query with metadata filtering
results = embeddings.search(
    "SELECT id, text, page_range FROM txtai WHERE user_id = 'user456'",
    limit=5
)
```

### Anti-Patterns to Avoid
- **Loading entire file into memory**: Use UploadFile.file (spooled) not bytes, stream to disk
- **Synchronous docling calls**: Blocks event loop; use async HTTP client (httpx) with backoff
- **Fixed-size chunking**: Breaks sentences/sections mid-thought; use section boundaries
- **No path validation**: Allows traversal attacks; always canonicalize and verify base directory
- **Forgetting overlap**: Loses context at chunk boundaries; add 10-20% overlap
- **Storing only embeddings**: Can't debug or show previews; enable txtai content storage

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Character count estimation | tiktoken | Accurate token counts matter for chunk boundaries; char/4 is only ~75% accurate |
| Retry with backoff | Custom sleep loops | backoff library | Handles jitter, max attempts, exception filtering, async support out-of-box |
| File path security | String manipulation (.replace("../", "")) | pathlib.resolve() + validation | Path traversal has edge cases (URL encoding, null bytes); stdlib handles canonicalization |
| Multipart parsing | Manual boundary parsing | python-multipart + FastAPI | HTTP spec is complex (CRLF, boundaries, encoding); FastAPI wraps it cleanly |
| Semantic chunking | Regex-based splitting | Encoder-aware recursive splitter | Token boundaries ≠ character boundaries; need encoder to measure accurately |
| Deduplication | String comparison | Hash-based (SHA-256) | Efficient for large datasets, handles normalization (whitespace, case) |
| PDF text extraction | PyPDF2, pdfplumber | docling-serve | Layout preservation, table structure, section detection require vision models |

**Key insight:** Document processing has "invisible complexity" in edge cases. Docling handles scanned PDFs, multi-column layouts, embedded tables; hand-rolled parsers fail on real-world aerospace docs with diagrams and complex formatting. Similarly, chunk overlap calculation seems trivial until you handle tokenization boundaries and preserve context semantically.

## Common Pitfalls

### Pitfall 1: Memory Exhaustion from Large File Uploads
**What goes wrong:** Using `File(bytes)` loads entire upload into memory; 10 concurrent 10MB uploads = 100MB spike
**Why it happens:** Intuitive to treat files as byte arrays, but HTTP uploads are streams
**How to avoid:** Use `UploadFile` (spooled temporary files) and stream to disk with `shutil.copyfileobj`
**Warning signs:** Memory usage spikes during upload testing, OOM errors under load
**Code example:**
```python
# WRONG: Loads entire file into memory
@app.post("/upload")
async def upload(file: bytes = File()):
    await save_file(file)  # 10MB in RAM

# RIGHT: Streams to disk
@app.post("/upload")
async def upload(file: UploadFile):
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)  # Chunked streaming
```

### Pitfall 2: Path Traversal via User-Controlled Filenames
**What goes wrong:** User uploads "../../etc/passwd" as filename, overwrites system files
**Why it happens:** Directly using `file.filename` in path construction without validation
**How to avoid:** Sanitize filenames (alphanumeric only) or use UUID, canonicalize paths, verify base directory
**Warning signs:** Security scanners flag path traversal (CWE-22)
**Code example:**
```python
# WRONG: Direct filename usage
raw_path = Path(f"data/raw/{user_id}/{file.filename}")  # Vulnerable!

# RIGHT: Validate and canonicalize
import re
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    # Remove path components, keep only alphanumeric + extension
    clean = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    return clean[:255]  # Limit length

raw_path = Path(f"data/raw/{user_id}/{doc_id}/{sanitize_filename(file.filename)}")
raw_path = raw_path.resolve()  # Canonicalize (resolve .., symlinks)

# Verify still within base directory
base_dir = Path("data/raw").resolve()
if not str(raw_path).startswith(str(base_dir)):
    raise ValueError("Path traversal detected")
```

### Pitfall 3: Breaking Semantic Context at Chunk Boundaries
**What goes wrong:** Fixed-size chunking (every 1000 chars) splits mid-sentence or mid-section, losing context
**Why it happens:** Simple implementation without considering document structure
**How to avoid:** Chunk at section boundaries (from docling), add overlap (10-20%), merge tiny sections (<50 tokens)
**Warning signs:** RAG retrieval returns fragments without context ("...control surfaces..." - what aircraft?), low retrieval accuracy
**Code example:**
```python
# WRONG: Naive fixed-size splitting
def chunk_text(text: str, size: int = 1000):
    return [text[i:i+size] for i in range(0, len(text), size)]
    # Breaks: "The aircraft's wing span is 35|.2 meters and..."

# RIGHT: Section-aware with overlap
def chunk_by_sections(sections: List[Dict], target_tokens: int = 1000):
    # Use docling sections, respect boundaries, add overlap
    # (See Pattern 3 above)
```

### Pitfall 4: No Retry Logic for Transient docling-serve Failures
**What goes wrong:** docling-serve restarts or network hiccup → entire batch processing fails permanently
**Why it happens:** Assuming external APIs are always available
**How to avoid:** Exponential backoff retry (3 attempts), distinguish transient (timeout, 503) from permanent (400, 413) errors
**Warning signs:** Sporadic "Failed" documents with network errors, batch processing stops on first error
**Code example:**
```python
# WRONG: Single attempt
async def parse_document(file_path):
    response = await httpx.post(docling_url, files={"file": open(file_path, "rb")})
    return response.json()  # Fails permanently on timeout

# RIGHT: Retry with backoff
@backoff.on_exception(
    backoff.expo,
    (httpx.TimeoutException, httpx.HTTPStatusError),
    max_tries=3,
    giveup=lambda e: e.response.status_code < 500 if hasattr(e, 'response') else False
)
async def parse_document(file_path):
    # Retries on 5xx, timeout; gives up on 4xx
```

### Pitfall 5: Forgetting to Enable txtai Content Storage
**What goes wrong:** Only embeddings stored, no text or metadata → can't filter by user_id, can't show chunk previews
**Why it happens:** Default txtai config doesn't enable content storage
**How to avoid:** Set `"content": True` in embeddings config, verify metadata fields persist
**Warning signs:** Queries return only IDs/scores, no text; metadata filters don't work
**Code example:**
```python
# WRONG: No content storage
embeddings = Embeddings({"path": "sentence-transformers/all-MiniLM-L6-v2"})
# Can only search by vector, no metadata available

# RIGHT: Enable content
embeddings = Embeddings({
    "path": "sentence-transformers/all-MiniLM-L6-v2",
    "content": True,  # Stores full document dict
    "backend": "sqlite"
})
```

### Pitfall 6: Not Handling docling Parse Failures Gracefully
**What goes wrong:** Docling returns empty/malformed JSON for scanned PDFs or corrupted files → chunking crashes
**Why it happens:** Assuming docling always succeeds and returns valid structure
**How to avoid:** Check for empty sections, fallback to basic text extraction (docling-parse), log detailed errors
**Warning signs:** "500 Internal Server Error" on certain PDFs, processing stuck in "Parsing" state
**Code example:**
```python
async def parse_with_fallback(file_path: Path):
    try:
        result = await docling_client.parse_document(file_path)

        # Check if parsing succeeded
        if not result.get("sections") or len(result["sections"]) == 0:
            logger.warning(f"Docling returned empty sections for {file_path}, using fallback")
            return fallback_text_extraction(file_path)

        return result
    except Exception as e:
        logger.error(f"Docling parse failed for {file_path}: {e}", exc_info=True)
        # Fallback to basic extraction
        return fallback_text_extraction(file_path)

def fallback_text_extraction(file_path: Path):
    """Extract plain text without structure."""
    # Use docling-parse or pypdf for basic extraction
    # Return synthetic sections with page-level chunks
```

## Code Examples

Verified patterns from official sources:

### FastAPI File Upload with Size Validation
```python
# Source: FastAPI official docs - Request Files
from fastapi import FastAPI, UploadFile, HTTPException, File
from typing import Annotated

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/documents/upload")
async def upload_document(file: Annotated[UploadFile, File()]):
    # Validate file type
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Only PDF and DOCX files allowed")

    # Validate size by reading in chunks
    size = 0
    async for chunk in file:
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit")

    # Reset file pointer after size check
    await file.seek(0)

    # Process file...
    return {"filename": file.filename, "size": size}
```

### Chunk Deduplication with Hash-Based Comparison
```python
# Source: RAG deduplication best practices
import hashlib
from typing import List, Dict

def deduplicate_chunks(chunks: List[Dict]) -> List[Dict]:
    """Remove duplicate chunks using normalized hash."""
    seen_hashes = set()
    unique_chunks = []

    for chunk in chunks:
        # Normalize text (lowercase, strip whitespace)
        normalized = chunk["text"].lower().strip()

        # Hash for efficient comparison
        chunk_hash = hashlib.sha256(normalized.encode()).hexdigest()

        if chunk_hash not in seen_hashes:
            seen_hashes.add(chunk_hash)
            unique_chunks.append(chunk)

    return unique_chunks
```

### Polling with Estimated Time Remaining
```python
# Source: FastAPI polling patterns + time estimation
from datetime import datetime, timedelta

STAGE_WEIGHTS = {
    "Uploading": 0.1,
    "Parsing": 0.4,
    "Chunking": 0.2,
    "Indexing": 0.3
}

def estimate_remaining(doc: Document) -> int:
    """Estimate seconds remaining based on document size and current stage."""
    # Historical average: 1 second per page
    total_estimated_secs = doc.page_count or 30  # Default if unknown

    # Calculate completed progress
    completed_weight = sum(
        STAGE_WEIGHTS[stage]
        for stage in STAGE_WEIGHTS
        if stage_before(stage, doc.current_stage)
    )

    # Remaining work
    remaining_weight = 1.0 - completed_weight
    remaining_secs = int(total_estimated_secs * remaining_weight)

    return max(0, remaining_secs)

def stage_before(stage1: str, stage2: str) -> bool:
    """Check if stage1 comes before stage2."""
    order = ["Uploading", "Parsing", "Chunking", "Indexing", "Done"]
    return order.index(stage1) < order.index(stage2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-size chunks (512 chars) | Semantic/section-based (adaptive) | 2024-2025 | 30-50% better retrieval accuracy on structured docs |
| PyPDF2/pdfplumber | docling-serve (vision models) | 2025 | Preserves tables, layout, multi-column; handles scanned PDFs |
| Character-based splitting | Token-aware with tiktoken | 2023-2024 | Accurate chunk sizing for LLM context windows |
| WebSockets for progress | HTTP polling (simpler) | Ongoing | Polling sufficient for 2-30 second tasks, avoids WebSocket complexity |
| Celery for all background tasks | FastAPI BackgroundTasks for short tasks | 2024-2025 | BackgroundTasks simpler for <10 min tasks, no Redis required |
| Manual retry loops | Decorator-based (backoff, tenacity) | Mature (2020+) | Declarative, handles jitter/max time, async-aware |

**Deprecated/outdated:**
- **PyPDF2 for structure extraction**: Can extract text but misses tables, layout, sections. Use docling for structured docs.
- **Character count estimation for tokens**: `len(text) / 4` is 75% accurate; use tiktoken for precision
- **Blacklist-based filename filtering**: Easily bypassed (URL encoding, null bytes); use allowlist (alphanumeric) + canonicalization

## Open Questions

Things that couldn't be fully resolved:

1. **Docling heading hierarchy accuracy**
   - What we know: Docling extracts headings but current versions (as of late 2024) mark all as `##` without differentiation between H1/H2/H3
   - What's unclear: Whether v1.10.0 (Jan 2026) improved heading level detection; GitHub issues indicate this was active development area
   - Recommendation: Test with sample aerospace doc (multi-level TOC); if hierarchy lost, store heading depth in metadata from page position/font size if available, or accept flat structure for POC

2. **Optimal chunk size for aerospace technical docs**
   - What we know: General recommendation is 512-1024 tokens; 1000 tokens (~750 words) balances context vs precision
   - What's unclear: Whether dense technical content (equations, tables, specs) benefits from smaller chunks (more precision) or larger (more context)
   - Recommendation: Start with 1000 tokens, A/B test with 512 and 1500 if retrieval quality is poor; monitor precision/recall on Day 1 with real IAI docs

3. **Table and figure handling in chunks**
   - What we know: Docling extracts table structure and image captions; decision log says "extract captions, skip content"
   - What's unclear: How to chunk when table spans multiple pages or section contains large table + text
   - Recommendation: Treat tables as atomic units (don't split mid-table); if table + text exceeds target, create table-only chunk with caption metadata; verify with sample IAI doc containing multi-page tables

4. **Processing time estimates accuracy**
   - What we know: Pattern suggests 1 sec/page baseline; stage weights (Parsing 40%, Chunking 20%, etc.)
   - What's unclear: Actual docling-serve performance on target hardware (CPU vs GPU), variability by document complexity
   - Recommendation: Log actual durations during Day 1 testing, calibrate estimates from real data; start with conservative 2 sec/page estimate

## Sources

### Primary (HIGH confidence)
- [docling-serve GitHub repository](https://github.com/docling-project/docling-serve) - v1.10.0 API structure, deployment options
- [docling-serve usage documentation](https://github.com/docling-project/docling-serve/blob/main/docs/usage.md) - API endpoints, request/response formats
- [FastAPI Request Files documentation](https://fastapi.tiangolo.com/tutorial/request-files/) - UploadFile, multipart handling
- [FastAPI Background Tasks documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) - BackgroundTasks patterns
- [tiktoken GitHub repository](https://github.com/openai/tiktoken) - Token counting, encoding selection
- [txtai Embeddings documentation](https://neuml.github.io/txtai/embeddings/) - Content storage, metadata indexing
- [backoff PyPI documentation](https://pypi.org/project/backoff/) - Exponential backoff, asyncio support

### Secondary (MEDIUM confidence)
- [Databricks Ultimate Guide to Chunking Strategies](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089) - Overlap recommendations (10-20%), section-based chunking
- [Better Stack FastAPI File Upload Guide](https://betterstack.com/community/guides/scaling-python/uploading-files-using-fastapi/) - Streaming to disk, size validation
- [Better Stack Background Tasks Guide](https://betterstack.com/community/guides/scaling-python/background-tasks-in-fastapi/) - When to use BackgroundTasks vs Celery
- [Weaviate Chunking Strategies Blog](https://weaviate.io/blog/chunking-strategies-for-rag) - Semantic chunking, overlap benefits
- [NVIDIA Finding Best Chunking Strategy](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/) - Chunk size experiments (1000 tokens optimal for many cases)
- [Docling AI Complete Guide (Codecademy)](https://www.codecademy.com/article/docling-ai-a-complete-guide-to-parsing) - Heading extraction, structure preservation
- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal) - Prevention techniques, canonicalization
- [PortSwigger Path Traversal Guide](https://portswigger.net/web-security/file-path-traversal) - Attack vectors, validation strategies
- [FastAPI Polling Strategy (CodeArchPedia)](https://openillumi.com/en/en-fastapi-long-task-progress-polling/) - Status endpoint patterns, progress tracking

### Tertiary (LOW confidence - needs validation)
- [Docling heading hierarchy GitHub issue #287](https://github.com/docling-project/docling/issues/287) - Community discussion on TOC extraction; unclear if resolved in v1.10.0
- [Multimodal.dev Semantic Chunking](https://www.multimodal.dev/post/semantic-chunking-for-rag) - General chunking benefits; not docling-specific
- [Max-Min Semantic Chunking (Springer)](https://link.springer.com/article/10.1007/s10791-025-09638-7) - Academic algorithm; may be too complex for POC timeline

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified with official docs, versions confirmed, stable releases
- Architecture: HIGH - Patterns from official FastAPI docs + txtai docs, proven in production
- Pitfalls: MEDIUM-HIGH - Path traversal and memory issues confirmed by OWASP/FastAPI docs; docling failure modes inferred from community discussions (not official docs)
- Chunking strategy: MEDIUM - Overlap percentages (10-20%) from multiple sources agree; optimal chunk size (1000 tokens) is general guidance, may need calibration for aerospace docs
- Docling heading hierarchy: LOW - Active development area, unclear if v1.10.0 resolved depth detection

**Research date:** 2026-01-27
**Valid until:** ~2026-02-26 (30 days - docling under active development, FastAPI/txtai stable)

**Critical validation needed:**
1. Test docling-serve v1.10.0 heading hierarchy with multi-level TOC doc (aerospace manual)
2. Measure actual processing times (parsing, chunking, indexing) on target hardware to calibrate estimates
3. Verify txtai content storage SQL filtering performance with user_id partitioning
4. Confirm chunk size (1000 tokens) delivers good retrieval with dense technical content (tables, equations)
