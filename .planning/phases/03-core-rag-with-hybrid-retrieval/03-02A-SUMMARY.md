---
phase: 03-core-rag-with-hybrid-retrieval
plan: 02A
subsystem: retrieval
tags: [txtai, hybrid-search, bm25, semantic-search, openai, embeddings, rrf]

# Dependency graph
requires:
  - phase: 02-document-processing-pipeline
    provides: TxtaiIndexer with basic semantic search and chunk storage
  - phase: 03-01
    provides: OpenAI embedding model configuration
provides:
  - Hybrid search capability combining semantic and BM25 retrieval
  - OpenAI text-embedding-3-small integration for production embeddings
  - Re-indexing without duplication (INDEX-05 compliance)
affects: [03-02B, 03-03, 03-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hybrid search with txtai (semantic + BM25 with RRF-equivalent fusion)"
    - "OpenAI embeddings with local model fallback"
    - "Normalized BM25 scoring for proper score fusion"

key-files:
  created: []
  modified:
    - backend/app/services/indexer.py

key-decisions:
  - "Use txtai's built-in hybrid search with normalize=True for RRF-equivalent fusion"
  - "Fetch 2x limit for post-filtering (user_id + threshold) to ensure enough results"
  - "Default weights=0.5 for equal semantic/BM25 balance (configurable per query)"

patterns-established:
  - "hybrid_search method as primary retrieval interface (replaces basic search)"
  - "reindex_document method for clean re-ingestion without duplication"

# Metrics
duration: 3min
completed: 2026-01-29
---

# Phase 03 Plan 02A: Hybrid Search Capability Summary

**Dual-channel retrieval (semantic + BM25) with OpenAI embeddings and normalized score fusion for technical document search**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-28T23:36:18Z
- **Completed:** 2026-01-28T23:39:39Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Enabled hybrid search in TxtaiIndexer combining semantic and BM25 retrieval
- Integrated OpenAI text-embedding-3-small embeddings with local model fallback
- Added reindex_document method to prevent chunk duplication on re-ingestion
- Configured normalized BM25 scoring for RRF-equivalent fusion

## Task Commits

Each task was committed atomically:

1. **Task 1: Enable hybrid search in TxtaiIndexer** - `f83fb3b` (feat)
2. **Task 2: Ensure de-duplication on re-ingestion (INDEX-05)** - `7d6785d` (feat)

## Files Created/Modified
- `backend/app/services/indexer.py` - Added hybrid search with OpenAI embeddings, reindex_document method, and normalized BM25 scoring

## Decisions Made

**1. Use txtai's built-in hybrid search with normalize=True**
- Rationale: txtai provides native hybrid search support with normalized BM25 scores that enable proper fusion equivalent to Reciprocal Rank Fusion (RRF)
- Alternative considered: Manual RRF implementation
- Outcome: Simpler, more maintainable, leverages battle-tested library code

**2. Fetch 2x limit for post-filtering**
- Rationale: User filtering and threshold filtering happen after retrieval, so we need to fetch more results than requested to ensure we have enough after filtering
- Impact: More results retrieved from index, but ensures accurate result counts

**3. Default weights=0.5 for equal semantic/BM25 balance**
- Rationale: Technical documents benefit from both semantic understanding (concepts) and exact term matching (technical jargon, model numbers)
- Configurable: weights parameter allows tuning per query if needed
- Aligns with: HYBRID_WEIGHT=0.5 from config.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation straightforward with txtai's native hybrid search support.

## User Setup Required

**OpenAI API key required for production embeddings.**

To use OpenAI embeddings (text-embedding-3-small):
1. Set `OPENAI_API_KEY` environment variable
2. Indexer will automatically use OpenAI embeddings on next initialization

Fallback behavior:
- If `OPENAI_API_KEY` is not set, indexer falls back to sentence-transformers/all-MiniLM-L6-v2 (local model)
- Warning logged: "openai_key_missing" with fallback model name

## Next Phase Readiness

**Ready for retrieval service implementation (03-02B)**
- Hybrid search capability complete
- OpenAI embeddings configurable
- Re-indexing without duplication verified
- User filtering and threshold filtering operational

**Blockers/Concerns:**
None - hybrid retrieval foundation is solid.

**Next steps:**
- 03-02B: Create retrieval service that uses hybrid_search
- 03-03: Integrate reranker for precision boost
- 03-04: Add chat endpoint with generation

---
*Phase: 03-core-rag-with-hybrid-retrieval*
*Completed: 2026-01-29*
