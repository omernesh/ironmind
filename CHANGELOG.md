# Changelog

All notable changes to IRONMIND will be documented in this file.

## [Unreleased]

### Added
- Demo collection feature for shared sample documents across all users (in progress)

### Fixed
- **Chunker nested document structure handling** (commit bd59f99)
  - Fixed `_extract_text()` to handle both nested `{"document": {"md_content": ...}}` and flat structures
  - Resolved issue where documents were processed as empty (chunk_count: 0)

- **Emergency split final chunk token limit** (commit c0934e6)
  - Applied token limit check to final chunk in emergency split
  - Fixed assertion failures on large chunks exceeding 10K tokens
  - Prevents "Emergency split failed: X > 10000" errors

- **Production deployment authentication** (Jan 31, 2026)
  - Added missing `JWT_SECRET_KEY` and `JWT_ALGORITHM` to production environment
  - Synchronized AUTH_SECRET between frontend and backend
  - Resolved JWT signature verification failures (401 errors)

- **Production code deployment**
  - Updated production server with latest chunker fixes
  - Force rebuilt backend container with `--no-cache` to ensure code updates

### Verified Working
- ✅ Document upload and processing pipeline
- ✅ Docling parsing with LibreOffice integration
- ✅ Hybrid chunking producing 13-44 chunks per document
- ✅ Entity extraction (90 entities per document average)
- ✅ Relationship extraction (35 relationships per document average)
- ✅ FalkorDB graph storage and indexing
- ✅ Production deployment at https://ironmind.chat

## [2026-01-31] - Production Validation

### Production Environment
- **Server**: Hetzner VPS at 65.108.249.67
- **Domain**: ironmind.chat, api.ironmind.chat
- **SSL**: Automatic TLS via Caddy
- **Deployment**: Docker Compose with 4 Gunicorn workers

### Test Documents Processed
Successfully indexed 10 aerospace technical documents:
1. D74879A-1.docx - 44 chunks
2. FC-00120-081000_C_1.DOCX - 38 chunks
3. D92050A-1.docx - 41 chunks
4. FC-130-04127_A_1.docx - 13 chunks
5. FC-00390-214000_B_1.docx - 5 chunks
6. FC07047A-1.docx - (processing)
7. FC-20180-081000_D_1.docx - (processing)
8. FC55005C-1.docx - (processing)
9. FC55021C-1.docx - (processing)
10. B-620-00234_A_1.docx - (processing)

### Performance Metrics
- Average processing time: ~90 seconds per document
- Token counting: tiktoken cl100k_base encoding
- Target chunk size: 1000 tokens
- Maximum chunk size: 10000 tokens (enforced)
- Overlap: 15%

## [2026-01-29] - Chunker Implementation

### Changed
- Replaced custom semantic chunker with Chonkie library
- Implemented hybrid mode combining semantic and token-based chunking
- Added configurable chunking parameters via environment variables

### Technical Details
- Chonkie version: 1.5.4+
- Embedding model: minishlab/potion-base-32M
- Semantic threshold: 0.5
- Model cache: /app/models

---

## Development Notes

### Architecture Decisions
- **Chunking Strategy**: Hybrid semantic + token-based for optimal balance
- **Authentication**: Better Auth (frontend) + JWT validation (backend)
- **Deployment**: Single-server Docker Compose (suitable for POC)
- **Database**: FalkorDB (Redis-compatible graph database)

### Known Issues
- B-620-00234_A_1.docx stuck in processing since Jan 29 (requires investigation)
- Document limit set to 10 per user (configurable)

### Next Steps
1. Implement demo collection for shared sample documents
2. Add document re-processing capability
3. Investigate stuck processing jobs
4. Add bulk document operations
5. Implement document search/filter in dashboard
