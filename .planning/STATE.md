# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-27)

**Core value:** Accurate, grounded answers from technical documentation with multi-source synthesis and transparent traceability
**Current focus:** Phase 2 - Document Processing Pipeline

## Current Position

Phase: 3 of 6 (Core RAG with Hybrid Retrieval)
Plan: 4 of 5 in current phase
Status: In progress
Last activity: 2026-01-29 - Completed 03-03-PLAN.md (Reranker Service)

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: 22 min
- Total execution time: 5.61 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure-foundation | 5/5 | 4.3h | 52m |
| 02-document-processing-pipeline | 5/5 | 62m | 12m |
| 03-core-rag-with-hybrid-retrieval | 4/5 | 17m | 4m |

**Recent Trend:**
- Last 5 plans: 02-05 (5m), 03-01 (3m), 03-02A (3m), 03-04 (5m), 03-03 (6m)
- Trend: Fast model/API tasks ~3-6min, chunking/indexing ~25min, gap closure/bug fixes ~5min

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Architecture: txtai for RAG backend (lightweight, native hybrid search)
- Architecture: FalkorDB for knowledge graph (lighter than Neo4j, POC-appropriate)
- Architecture: docling-serve API (separate service for document processing)
- Architecture: OpenAI text-embedding-3-small (cost-effective embeddings)
- Architecture: Mistral rerank via DeepInfra (30-50% precision boost)
- Architecture: Hybrid RAG (BM25 + embeddings for technical docs)
- Architecture: OpenAI GPT-5-mini (latest model, faster than GPT-4)
- Timeline: 5-day deadline (Feb 1, 2026) requires aggressive execution

**From 01-01 execution:**
- Implementation: Pydantic-settings for environment configuration
- Implementation: Structlog with JSON output for production, console for development
- Implementation: BaseHTTPMiddleware for request logging (avoids async context issues)
- Implementation: Middleware order: CORS → CorrelationID → RequestLogging
- Implementation: Gunicorn with Uvicorn workers for production deployment
- Implementation: Non-root user (appuser) in Docker for security

**From 01-02 execution:**
- Implementation: Better Auth with SQLite for POC simplicity (no Postgres required)
- Implementation: Email verification disabled for POC speed (requireEmailVerification: false)
- Implementation: 7-day session expiry with cookie-based persistence
- Implementation: TypeScript types required for better-sqlite3 native module
- Implementation: Multi-stage Docker build with native module compilation support

**From 01-03 execution:**
- Implementation: FastAPI Depends injection for JWT validation (not global middleware)
- Implementation: Extract user_id from 'sub' claim (Better Auth convention)
- Implementation: Structlog context binding for user_id in logs
- Implementation: Optional authentication dependency for mixed endpoints
- Implementation: HS256 algorithm for JWT (symmetric key)

**From 01-04 execution:**
- Implementation: Shared AUTH_SECRET for JWT validation between frontend and backend
- Implementation: Docker Compose override pattern for development with volume mounts
- Implementation: FalkorDB with --protected-mode no for POC (no password)
- Implementation: Named network (ironmind-network) for service-to-service communication
- Implementation: Service health checks with depends_on for startup ordering

**From 01-05 execution:**
- Implementation: Token exchange pattern (Better Auth session -> JWT token via /api/auth/backend-token)
- Implementation: Jose library for JWT creation (ESM-native, Next.js compatible)
- Implementation: 15-minute token expiry with 1-minute refresh buffer and in-memory caching
- Implementation: Manual database schema creation (Better Auth v1.4.17 doesn't auto-create)
- Implementation: WAL mode enabled for better SQLite concurrency
- Implementation: Browser uses localhost:8000, server-side uses backend:8000 for API calls

**From 02-01 execution:**
- Implementation: ProcessingStatus enum with 6 states (Uploading, Parsing, Chunking, Indexing, Done, Failed)
- Implementation: Processing log stored as JSON in SQLite for flexible stage tracking
- Implementation: Path security via resolve() + is_relative_to() validation (prevents symlink/traversal attacks)
- Implementation: Filename sanitization regex [^a-zA-Z0-9._-] with directory component stripping
- Implementation: Directory structure /data/{raw,processed}/{user_id}/{doc_id}/ for isolation
- Implementation: ChunkMetadata format doc_id-chunk-NNN for human-readable debugging
- Implementation: aiosqlite with WAL mode for concurrent reads during processing

**From 02-02 execution:**
- Implementation: Streaming file validation (read chunks, validate size without loading entire file)
- Implementation: FastAPI BackgroundTasks for async document processing
- Implementation: DoclingClient with exponential backoff retry (@backoff.on_exception decorator)
- Implementation: httpx AsyncClient for docling-serve API integration
- Implementation: 120s timeout for docling parsing (PDFs with OCR can take time)
- Implementation: Retry only transient errors (timeout, 5xx); fail immediately on 4xx
- Implementation: Fixed docling-serve Docker image path (quay.io/docling-project/docling-serve:v1.10.0)

**From 02-03 execution:**
- Implementation: tiktoken cl100k_base encoding for token counting (GPT-3.5/4 compatible)
- Implementation: Target 1000 tokens per chunk with 15% overlap
- Implementation: Section-boundary chunking (never splits mid-section)
- Implementation: Merge small sections (<50 tokens), split large sections (>1500 tokens) at paragraph boundaries
- Implementation: SHA-256 hash-based deduplication (lowercase + strip normalization)
- Implementation: txtai content storage enabled (CRITICAL for metadata persistence)
- Implementation: sentence-transformers/all-MiniLM-L6-v2 as fallback embeddings for POC
- Implementation: SQLite backend for txtai index persistence
- Implementation: User-based filtering for multi-tenant chunk isolation
- Implementation: Config extra='ignore' to allow additional env vars without validation errors

**From 02-04 execution:**
- Implementation: DocumentPipeline orchestration pattern (single service coordinates parse -> chunk -> index)
- Implementation: Status API returns INGEST-10 compliant values (Processing, Indexed, Failed) with internal_status for debugging
- Implementation: Progress percentage via stage weights: Uploading (10%), Parsing (40%), Chunking (20%), Indexing (30%)
- Implementation: Time estimation ~2 sec/page baseline with remaining work from stage weights
- Implementation: doc_ingestion event logging (started, completed, failed) with metrics
- Implementation: Processing log as structured JSON with stage timing data
- Implementation: Failure handling cleans up files (delete raw and processed on error)

**From 02-05 execution:**
- Implementation: Markdown heading pattern matching (#{1,6}) for section extraction from docling md_content
- Implementation: Character position-based page estimation (~3000 chars/page heuristic)
- Implementation: Multi-format extraction fallback chain (document.md_content → sections → pages → text)
- Implementation: Format adapter pattern for docling v1.10.0 output compatibility

**From 03-01 execution:**
- Implementation: OpenAI text-embedding-3-small for embeddings ($0.02/1M tokens, 1536 dimensions)
- Implementation: DeepInfra Qwen/Qwen3-Reranker-0.6B for reranking (30-50% precision boost)
- Implementation: OpenAI GPT-5-mini for generation (latest model, 0.1 temperature for factual accuracy)
- Implementation: Three-stage retrieval funnel (25 initial → 12 reranked → 10 to LLM)
- Implementation: Hybrid search 50/50 weight (HYBRID_WEIGHT=0.5 for BM25 + semantic)
- Implementation: Citation model with doc_id, filename, page_range, snippet for traceability
- Implementation: DiagnosticInfo model for latency tracking (retrieval, rerank, generation stages)
- Implementation: ChatRequest validation (1-2000 chars question, required user_id)
- Implementation: Dependencies added: litellm>=1.0.0, openai>=1.0.0, redis>=5.0.0

**From 03-02A execution:**
- Implementation: Hybrid search enabled in TxtaiIndexer (hybrid=True with BM25 + semantic)
- Implementation: OpenAI embeddings with local fallback (text-embedding-3-small when API key available)
- Implementation: Normalized BM25 scoring (normalize=True for RRF-equivalent fusion)
- Implementation: hybrid_search method with user filtering and threshold
- Implementation: reindex_document method for clean re-ingestion (INDEX-05 compliance)
- Implementation: Fetch 2x limit for post-filtering to ensure enough results after user_id + threshold filtering

**From 03-04 execution:**
- Implementation: Generator service using AsyncOpenAI with GPT-5-mini (30s timeout)
- Implementation: Grounded prompt with SYSTEM_PROMPT enforcing "ONLY from documents" responses
- Implementation: Context building with numbered citations [N: filename, p.X]
- Implementation: Empty chunks return user-friendly "cannot find information" message
- Implementation: Conversation history support (last 10 messages = 5 turns)
- Implementation: Citation objects with 200-char snippets for previews
- Implementation: Diagnostics tracking (latency_ms, tokens_used) for observability

**From 03-03 execution:**
- Implementation: Reranker service with DeepInfra Qwen3-Reranker-0.6B integration
- Implementation: Cross-encoder reranking for 30-50% precision boost over semantic-only retrieval
- Implementation: Graceful error handling (missing API key → skip, API error → fallback to input order)
- Implementation: Rerank score and rank metadata attached to chunks for diagnostics
- Implementation: Score distribution logging (min/max/avg) for performance monitoring
- Implementation: Latency tracking for reranking stage observability

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 Risks:**

- ~~Docling integration requires Day 1 validation on actual aerospace documents~~ **RESOLVED:** Complete ingestion pipeline verified end-to-end in 02-04
- ~~Better Auth configuration complexity may delay auth implementation~~ **RESOLVED:** Better Auth configured with SQLite (01-02)
- ~~Docker Compose orchestration with 4+ services needs testing~~ **RESOLVED:** Docker Compose verified with all services healthy (01-04)
- ~~End-to-end auth flow needs verification~~ **RESOLVED:** Complete auth flow verified in 01-05 (register -> login -> dashboard -> backend API -> logout)

**Phase 2 Complete (Gap Closure Verified):**

- Document processing pipeline fully operational: upload -> parse -> chunk -> index
- Format mismatch resolved: chunker now extracts sections from docling md_content format
- Semantic chunking produces actual chunks (verified: 4-5 chunks from test documents)
- Status polling API ready for frontend integration (Phase 6)
- INGEST-10 backend contract complete (UI display is Phase 6 scope)

**Phase 3 In Progress:**

- Plan 03-01 complete: RAG configuration and chat models established
- Plan 03-02A complete: Hybrid search capability with OpenAI embeddings
- Plan 03-03 complete: Reranker service with DeepInfra Qwen3-Reranker-0.6B
- Plan 03-04 complete: Answer generation service with GPT-5-mini
- Ready for chat API endpoint (03-05) - final plan in Phase 3
- API keys needed: OPENAI_API_KEY and DEEPINFRA_API_KEY (see 03-01-SUMMARY.md)

**Phase 4 Risks (Research Flag):**

- Knowledge graph entity extraction quality highly domain-dependent
- 70% accuracy threshold may be difficult to achieve without manual tuning
- Research suggests 30-40% incorrect edges without entity resolution

**Phase 6 Risks (Research Flag):**

- LobeChat-custom backend integration pattern less documented
- IAI branding customization depth unknown

## Session Continuity

Last session: 2026-01-29 01:43
Stopped at: Completed 03-03-PLAN.md (Reranker Service)
Resume file: None
Next action: Execute 03-05-PLAN.md (Chat API Endpoint) - final plan in Phase 3
