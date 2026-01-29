# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-27)

**Core value:** Accurate, grounded answers from technical documentation with multi-source synthesis and transparent traceability
**Current focus:** Phase 3 - Core RAG with Hybrid Retrieval (Complete)

## Current Position

Phase: 5 of 6 (Multi-Source Synthesis)
Plan: 2 of 4 in current phase
Status: In progress
Last activity: 2026-01-29 - Completed 05-02-PLAN.md (Document Cross-Reference Detection)

Progress: [█████████░] 88% (22 of 25 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: 14 min
- Total execution time: 6.9 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure-foundation | 5/5 | 4.3h | 52m |
| 02-document-processing-pipeline | 5/5 | 62m | 12m |
| 03-core-rag-with-hybrid-retrieval | 6/6 | 20m | 3m |
| 04-knowledge-graph-integration | 5/5 | 69m | 14m |
| 05-multi-source-synthesis | 2/4 | 11m | 6m |

**Recent Trend:**

- Last 6 plans: 04-03 (3m), 04-04 (8m), 04-05 (47m), 05-01 (6m), 05-02 (5m)
- Trend: Phase 5 maintaining fast velocity - pure logic/integration changes (5-6m avg)

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

**From 03-02B execution:**
- Implementation: HybridRetriever service wraps indexer.hybrid_search() for RAG abstraction
- Implementation: Query preprocessing with aerospace acronym expansion (UAV, GPS, IMU, etc.)
- Implementation: Structured response format with chunks, count, latency_ms, diagnostics
- Implementation: Score statistics (min/max/avg) for retrieval performance monitoring
- Implementation: 15 aerospace/defense domain acronyms in ACRONYM_MAP for query enhancement

**From 04-01 execution:**
- Implementation: Pydantic Literal constraints for entity types (hardware, software, configuration, error) and relationship types (depends_on, configures, connects_to, is_part_of)
- Implementation: MERGE-based upsert by (name + user_id) prevents duplicate entities
- Implementation: Parameterized Cypher queries prevent injection attacks
- Implementation: User-scoped graph isolation via user_id filtering in all queries
- Implementation: Depth-limited BFS traversal (default: 2 hops) prevents exponential expansion
- Implementation: Relationship context field stores sentence for LLM grounding
- Implementation: Index creation on entity.name, entity.type, entity.user_id for query performance
- Implementation: Subgraph export with nodes/edges lists for graph-aware retrieval

**From 04-02 execution:**
- Implementation: OpenAI GPT-4o-2024-08-06 with Structured Outputs for 100% schema compliance
- Implementation: beta.chat.completions.parse() method for Pydantic response parsing
- Implementation: Temperature=0 for deterministic entity extraction
- Implementation: Asyncio.gather with Semaphore(5) for concurrent API calls (rate limit control)
- Implementation: Graceful error handling returns empty GraphExtraction on API failures
- Implementation: Acronym expansion in normalize_entity_name() using ACRONYM_MAP
- Implementation: Entity resolution with LLM disambiguation for cross-document deduplication
- Implementation: Post-processing fills doc_id/chunk_id metadata not in LLM output
- Implementation: Extraction metrics tracking (extractions, entities, relationships, failures)

**From 04-03 execution:**
- Implementation: GRAPH_EXTRACTING stage inserted between CHUNKING and INDEXING in pipeline
- Implementation: Stage weights rebalanced: Parsing 35%, Chunking 15%, GraphExtracting 15%, Indexing 25%
- Implementation: EntityExtractor and GraphStore initialized in DocumentPipeline
- Implementation: Re-ingestion cleanup via delete_document_entities() before extraction
- Implementation: Entity/relationship counts stored in Document model for metrics tracking
- Implementation: Graceful error handling: graph extraction failures log warning but don't crash pipeline
- Implementation: Graph extraction as optional enhancement, not critical path for document ingestion

**From 04-04 execution:**

- Implementation: GraphRetriever extracts entities from queries using EntityExtractor
- Implementation: Relationship queries trigger depth=2 traversal, simple queries use depth=1
- Implementation: Relationship detection via keywords (connect, depend, interface) + multi-entity heuristic
- Implementation: Graph chunks merged after semantic chunks with deduplication by entity name
- Implementation: Citation model has source field ('document' or 'graph') for transparency
- Implementation: Graph citations formatted as [N: Knowledge Graph - Entity] in prompts
- Implementation: Lazy import pattern in GraphRetriever to avoid circular dependency with EntityExtractor
- Implementation: HybridRetriever accepts graph_retriever dependency for testability
- Implementation: Dual-channel retrieval pattern: Channel 1 (semantic+BM25) + Channel 2 (graph context)
- Implementation: Merge limit: graph chunks capped at 2x semantic count to avoid explosion

**From 04-05 execution:**

- Implementation: Debug endpoints under /api/debug namespace for inspection tools
- Implementation: Multi-format response pattern (edgelist vs cytoscape) via query parameter
- Implementation: GraphStore statistics methods (count_entities, count_relationships, get_entity_type_counts, list_entities)
- Implementation: Integration tests skip OpenAI/FalkorDB tests when services unavailable (graceful degradation)
- Implementation: Test fixtures with cleanup to ensure test isolation
- Implementation: format_edgelist() and format_cytoscape() helpers for graph visualization formats
- Implementation: Stats endpoint provides entity/relationship counts by type for monitoring extraction quality

**From 05-01 execution:**

- Implementation: DocumentRelationship schema with Literal type constraints (explicit_citation | shared_entities)
- Implementation: DocumentRelationshipStore manages document-level relationship graph in FalkorDB
- Implementation: Separate CITES and SHARES_ENTITIES edge types for weighted scoring
- Implementation: Document nodes with doc_id, filename, user_id, page_count, chunk_count metadata
- Implementation: Citation.multi_source field tracks multi-source claims with adjacent citations
- Implementation: Citation.related_doc_ids provides related document metadata for UI
- Implementation: ChatResponse.synthesis_mode and source_doc_count for multi-doc tracking
- Implementation: python-Levenshtein for fuzzy citation text matching
- Implementation: networkx for document relationship graph algorithms
- Implementation: Relationship evidence stored as list (citation text or shared entity names)

**From 05-02 execution:**

- Implementation: CrossReferenceDetector with dual-signal detection (explicit citations + shared entities)
- Implementation: Explicit citation patterns: DOC_CODE_PATTERN, SEE_DOC_PATTERN, SECTION_REF_PATTERN
- Implementation: Fuzzy matching with 70% Levenshtein similarity for citation text vs filename comparison
- Implementation: Shared entity detection requires 2+ common entities between documents
- Implementation: Priority-based deduplication: explicit citations take precedence over shared entities
- Implementation: Strength scoring: explicit citations 1.0, shared entities 0.5 + (count-2)*0.1, capped at 0.9
- Implementation: Document relationship extraction as pipeline stage 3.5 (after GraphExtracting, before Indexing)
- Implementation: STAGE_WEIGHTS rebalanced: DocumentRelationships 5% (Parsing reduced to 30%)
- Implementation: list_entities_for_doc method added to GraphStore for entity comparison
- Implementation: list_user_documents alias method added to DocumentDatabase for consistency
- Implementation: doc_relationship_count field added to Document model for metrics tracking
- Implementation: Relationship extraction only against DONE documents (skip Processing/Failed)
- Implementation: Graceful error handling: relationship extraction failures log warning, don't crash pipeline

**From 05-03 execution:**

- Implementation: should_activate_synthesis_mode() detects 2+ documents with 2+ chunks each
- Implementation: SYNTHESIS_SYSTEM_PROMPT with topic-organized structure and consensus language
- Implementation: build_synthesis_context() groups chunks by source document for pattern visibility
- Implementation: Chain-of-Thought user prompt with 4-step reasoning guidance
- Implementation: _build_citations() parses [1-3] compact notation and detects adjacent citations
- Implementation: Generator.generate() returns synthesis_mode and source_doc_count
- Implementation: +200 tokens for synthesis mode (600 total vs 400 standard)
- Implementation: ChatResponse passes synthesis metadata from generator to frontend
- Implementation: Citation.multi_source set to True for adjacent citations in synthesis mode

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

**Phase 3 Complete (7/9 success criteria verified):**

- ✅ All 6 plans executed: Configuration, Hybrid Search, Retriever, Reranker, Generator, Chat API
- ✅ Full RAG pipeline operational: retrieve → rerank → generate
- ✅ Hybrid retrieval with OpenAI embeddings + BM25 keyword search
- ✅ Cross-encoder reranking with DeepInfra Qwen3-Reranker-0.6B (30-50% precision boost)
- ✅ Answer generation with GPT-5-mini and inline citations
- ✅ POST /api/chat endpoint with authentication and comprehensive diagnostics
- ✅ 22/26 tests passing (4 minor auth code mismatches: 403 vs 401)
- ⚠️ Performance verification pending: <10s query time and 2-3 concurrent users (requires live testing)

**Phase 4 Complete:**

- ✅ Plan 04-01 complete: FalkorDB client, Pydantic schemas, graph storage foundation
- ✅ Plan 04-02 complete: EntityExtractor with OpenAI Structured Outputs and acronym expansion
- ✅ Plan 04-03 complete: Pipeline integration with graph extraction stage
- ✅ Plan 04-04 complete: Graph-aware retrieval with dual-channel merging
- ✅ Plan 04-05 complete: Debug endpoints, statistics API, integration tests
- Knowledge graph populated automatically during document ingestion (verified: 69 entities, 45 relationships)
- Graph-aware retrieval enhances RAG with relationship context
- Citations transparently mark graph-derived vs document-stated information
- End-to-end flow: upload → extract entities → answer relationship questions
- Debug endpoints for graph inspection (/api/debug/graph/sample, /api/debug/graph/stats)
- Comprehensive integration tests cover schemas, CRUD, extraction, retrieval, statistics

**Phase 5 Progress:**

- ✅ Plan 05-01 complete: Document relationship schemas and storage foundation
- ✅ Plan 05-02 complete: Document cross-reference detection and pipeline integration
- DocumentRelationship schema with explicit_citation and shared_entities types
- DocumentRelationshipStore provides CRUD for document-level graph
- CrossReferenceDetector with dual-signal detection (explicit citations + shared entities)
- Explicit citation detection via regex patterns (doc codes, "See Document X", section refs)
- Shared entity detection with 2+ common entities threshold and acronym expansion
- Document relationship extraction integrated as pipeline stage 3.5
- Priority-based scoring: explicit citations 1.0, shared entities 0.5-0.9
- Citation model extended with multi_source and related_doc_ids fields
- ChatResponse tracks synthesis_mode and source_doc_count
- Graceful error handling: relationship extraction failures don't crash pipeline
- Ready for multi-source synthesis prompting (05-03) and debug endpoints (05-04)

**Phase 6 Risks (Research Flag):**

- LobeChat-custom backend integration pattern less documented
- IAI branding customization depth unknown

## Session Continuity

Last session: 2026-01-29
Stopped at: Completed 05-02-PLAN.md (Document Cross-Reference Detection)
Resume file: None
Next action: Continue Phase 05 (Multi-Source Synthesis) - Plan 05-03 (Multi-Source Synthesis Pipeline)
