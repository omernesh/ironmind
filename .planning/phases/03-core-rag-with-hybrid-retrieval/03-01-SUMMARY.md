---
phase: 03-core-rag-with-hybrid-retrieval
plan: 01
subsystem: rag
tags: [openai, deepinfra, litellm, pydantic, embeddings, reranker, gpt-5-mini]

# Dependency graph
requires:
  - phase: 02-document-processing-pipeline
    provides: txtai index with semantic chunking and document storage
provides:
  - RAG pipeline configuration with OpenAI embeddings and DeepInfra reranker
  - Chat request/response models with citations and diagnostics
  - Hybrid search parameters (retrieval, rerank, context limits)
affects: [03-core-rag-with-hybrid-retrieval, 06-frontend-chat-ui]

# Tech tracking
tech-stack:
  added: [litellm>=1.0.0, openai>=1.0.0, redis>=5.0.0]
  patterns: [Pydantic validation for chat models, DiagnosticInfo for observability]

key-files:
  created: [backend/app/models/chat.py]
  modified: [backend/app/config.py, backend/requirements.txt, backend/app/models/__init__.py]

key-decisions:
  - "OpenAI text-embedding-3-small for embeddings (cost-effective, 1536 dimensions)"
  - "DeepInfra Qwen/Qwen3-Reranker-0.6B for reranking (30-50% precision boost)"
  - "OpenAI GPT-5-mini for generation (latest model, faster than GPT-4)"
  - "Hybrid search with 50/50 weight (HYBRID_WEIGHT=0.5)"
  - "Three-stage retrieval: 25 initial → 12 reranked → 10 to LLM"
  - "Low temperature (0.1) for factual accuracy in technical documentation"
  - "DiagnosticInfo model for performance observability and latency tracking"

patterns-established:
  - "Citation model with doc_id, filename, page_range, snippet for traceability"
  - "ChatRequest validation: question 1-2000 chars, user_id required"
  - "ChatResponse with answer, citations list, request_id, optional diagnostics"
  - "Three-tier filtering: retrieval_limit → rerank_limit → context_limit"

# Metrics
duration: 3min
completed: 2026-01-28
---

# Phase 03 Plan 01: Configuration and Data Models Summary

**OpenAI text-embedding-3-small embeddings, DeepInfra Qwen reranker, GPT-5-mini generation with hybrid search configuration and citation-based chat models**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-28T23:29:43Z
- **Completed:** 2026-01-28T23:32:14Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- RAG pipeline configuration with OpenAI and DeepInfra API keys
- Hybrid search parameters for 3-stage retrieval (25→12→10 chunks)
- Chat data models with citations for document traceability
- DiagnosticInfo model for performance monitoring

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend configuration for RAG pipeline** - `962e17f` (feat)
2. **Task 2: Create chat data models** - `26d9f63` (feat)

## Files Created/Modified
- `backend/app/config.py` - Added RAG pipeline settings (embeddings, reranker, LLM, hybrid search, cache)
- `backend/requirements.txt` - Added litellm, openai, redis dependencies
- `backend/app/models/chat.py` - Created ChatRequest, ChatResponse, Citation, DiagnosticInfo models
- `backend/app/models/__init__.py` - Exported chat models

## Decisions Made

**1. OpenAI text-embedding-3-small for embeddings**
- Rationale: Cost-effective ($0.02/1M tokens), 1536 dimensions, good performance on technical docs
- Alternative considered: all-MiniLM-L6-v2 (current fallback, lower quality)

**2. DeepInfra Qwen/Qwen3-Reranker-0.6B for reranking**
- Rationale: 30-50% precision boost over pure semantic search, fast inference
- DeepInfra provides hosted API (no local model deployment needed for POC)

**3. OpenAI GPT-5-mini for generation**
- Rationale: Latest model, faster than GPT-4, optimized for factual accuracy
- Temperature 0.1: Low for deterministic, factual answers from technical documentation

**4. Three-stage retrieval funnel (25→12→10)**
- RETRIEVAL_LIMIT=25: Cast wide net with hybrid search (BM25 + semantic)
- RERANK_LIMIT=12: Send top candidates to reranker for precision
- CONTEXT_LIMIT=10: Final context window to LLM (balances cost and relevance)
- RELEVANCE_THRESHOLD=0.3: Minimum score to include (prevents low-quality results)

**5. Hybrid search 50/50 weight**
- HYBRID_WEIGHT=0.5: Equal BM25 and semantic for technical docs (keyword + concept match)
- Adjustable based on domain (can tune toward BM25 for exact terminology, semantic for concepts)

**6. DiagnosticInfo for observability**
- Tracks latency at each stage: retrieval, rerank, generation
- Cache hit detection for performance optimization
- Enables debugging slow queries and monitoring API costs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Environment variables required for RAG pipeline:**

Before executing plan 03-02 (retrieval implementation), add to `.env`:

```bash
# OpenAI API (embeddings + LLM)
OPENAI_API_KEY=sk-...your-key...

# DeepInfra API (reranker)
DEEPINFRA_API_KEY=...your-key...
```

**To obtain API keys:**

1. **OpenAI:** https://platform.openai.com/api-keys
   - Create new secret key
   - Copy to OPENAI_API_KEY

2. **DeepInfra:** https://deepinfra.com/dash/api_keys
   - Sign up/login
   - Generate API key
   - Copy to DEEPINFRA_API_KEY

**Optional (for caching):**
- Redis not required for POC - in-memory caching will be used if Redis unavailable
- For production: add Redis service to docker-compose.yml

**Verification:**
```bash
python -c "from app.config import settings; print(settings.OPENAI_API_KEY[:10], settings.DEEPINFRA_API_KEY[:10])"
```

## Next Phase Readiness

**Ready for plan 03-02: Implement hybrid retrieval service**

- Configuration established: embeddings, reranker, LLM settings loaded
- Data models ready: ChatRequest/ChatResponse with validation
- Dependencies added: litellm, openai in requirements.txt
- txtai index from Phase 2 available for hybrid search

**No blockers.**

**Next steps:**
1. Plan 03-02: Implement txtai hybrid search with BM25+semantic
2. Plan 03-03: Implement DeepInfra reranker integration
3. Plan 03-04: Implement OpenAI LLM generation with citations
4. Plan 03-05: Create chat API endpoint with /api/chat POST

---
*Phase: 03-core-rag-with-hybrid-retrieval*
*Completed: 2026-01-28*
