# Phase 2: Document Processing Pipeline - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform uploaded documents (DOCX/PDF) into searchable chunks while preserving structure and metadata for accurate retrieval. Handles document upload through to indexed chunks stored with rich metadata. RAG retrieval and Q&A happen in Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Upload Flow
- **Upload modes:** Support both batch upload (up to 10 files at once) and single file upload - user choice
- **Validation strategy:** Client-side validation for fast UX feedback + server-side validation for security
- **File size limit:** 10 MB per document (covers typical PDFs/DOCX, fast processing)
- **Upload UX:** Both drag-and-drop area and file picker button
- **Progress display:** Overall progress indicator (not per-file bars)
- **Network retry:** Auto-retry 3 times for network failures during upload
- **Document limit enforcement:** Block upload in UI when user reaches 10 document limit (fetch current count, prevent upload client-side)

### Chunking Strategy
- **Target chunk size:** ~1000 tokens (medium chunks) - balanced context without fragmentation
- **Section boundaries:** Never cross section boundaries - each chunk stays within a section (may create uneven sizes but cleaner semantics)
- **Chunk overlap:** 10-20% overlap between consecutive chunks for context continuity
- **Short sections:** Merge sections < 50 tokens with next section until target size reached
- **Metadata (rich):** doc_id, page_range, filename, section_title, user_id, doc_type, author, timestamps
- **Page ranges:** Exact page spans (e.g., "5-7") for precise citations
- **Chunk IDs:** Format as `doc_id-chunk_index` (e.g., "doc123-chunk-001") for human-readable debugging
- **Document order:** Store chunk_index to preserve position in document
- **Chunk storage:** Store full chunk text (not just embeddings) for debugging and preview
- **Deduplication:** Deduplicate identical chunks across different documents
- **Re-upload handling:** Replace old chunks when user re-uploads same document
- **Unstructured docs:** Fall back to fixed-size 1000-token chunking when semantic chunking fails
- **Image handling:** Extract image captions as metadata (skip image content for POC)
- **Language:** Assume English only (no language detection)
- **Chunk validation:** No quality filtering - index all chunks from docling

### Error and Retry Handling
- **API failures:** Retry with exponential backoff (3 attempts) when docling-serve is unreachable
- **Parse failures:** Fall back to basic text extraction if docling returns low-quality/empty results
- **Partial success:** Index successful documents and report failures (e.g., 7/10 succeed - user can query those 7)
- **Error messages:** User-friendly only (no technical details exposed to users)
- **Failed document storage:** Delete failed documents immediately (don't store in /data/failed)
- **Manual retry:** Provide 'Retry' button per failed document in UI
- **Error logging:** Detailed logging with docling response and stack traces for debugging
- **Notifications:** In-app status only (no toast/alert notifications)

### Status Visibility
- **Status stages:** Detailed granularity - Uploading, Parsing, Chunking, Indexing, Done (also Failed)
- **Update mechanism:** Frontend polls backend every 2 seconds for status updates
- **Time estimates:** Show estimated processing time remaining based on document size/page count
- **Processing history:** Maintain and display processing log with timestamps for each stage, retries, failures

### Claude's Discretion
- File list confirmation before processing (process immediately vs review step)
- Table/figure handling during chunking (whole vs extracted items)
- Fallback extraction strategy details when docling fails
- Time estimate calculation algorithm
- Storage optimization for processing history

</decisions>

<specifics>
## Specific Ideas

- Success criteria requires per-file status (Processing, Indexed, Failed) - our detailed stages (Uploading, Parsing, Chunking, Indexing, Done) exceed this
- Aerospace documents likely have tables and diagrams - caption extraction ensures we don't lose figure references
- 10 MB limit chosen for POC speed vs coverage trade-off - may need adjustment after testing with real IAI docs on Day 1

</specifics>

<deferred>
## Deferred Ideas

- Knowledge graph entity extraction - Phase 4 (correctly scoped)
- Multi-language support - out of scope for POC
- WebSocket real-time updates - polling sufficient for POC
- Document versioning (keeping multiple versions) - replace-on-upload simpler for POC

</deferred>

---

*Phase: 02-document-processing-pipeline*
*Context gathered: 2026-01-27*
