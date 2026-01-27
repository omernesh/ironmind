# Requirements: IRONMIND - DocRAG POC for IAI

**Defined:** 2026-01-27
**Core Value:** Accurate, grounded answers from technical documentation with multi-source synthesis and transparent traceability

## v1 Requirements

Requirements for initial release (Feb 1, 2026 deadline). Each maps to roadmap phases.

### Authentication (AUTH)

- [x] **AUTH-01**: User can register with email and password via Better Auth
- [x] **AUTH-02**: User can log in and session persists across browser refresh
- [x] **AUTH-03**: Backend validates auth tokens/headers from frontend on all protected endpoints
- [x] **AUTH-04**: Backend extracts user_id from auth context for request tracking
- [x] **AUTH-05**: Unauthenticated requests to /api/ingest and /api/chat return HTTP 401

### Document Ingestion (INGEST)

- [ ] **INGEST-01**: User can upload DOCX/PDF documents via IRONMIND interface
- [ ] **INGEST-02**: System accepts up to 10 documents per user with configurable size limits
- [ ] **INGEST-03**: Backend calls docling-serve API to parse and extract structured content from uploads
- [ ] **INGEST-04**: System preserves document structure (sections, headings, page numbers) during parsing
- [ ] **INGEST-05**: System uses semantic chunking (not fixed-size) to preserve context boundaries
- [ ] **INGEST-06**: Each chunk includes metadata (doc_id, filename, page_range, section_title, user_id)
- [ ] **INGEST-07**: System stores original files to /data/raw/{user_id}/{doc_id}
- [ ] **INGEST-08**: System stores processed output to /data/processed/{user_id}/{doc_id}
- [ ] **INGEST-09**: Upload endpoint returns per-file status (filename, status, error if any)
- [ ] **INGEST-10**: User can see document status in UI (Processing, Indexed, Failed)

### Indexing & Storage (INDEX)

- [ ] **INDEX-01**: System indexes chunks in txtai using OpenAI text-embedding-3-small embeddings
- [ ] **INDEX-02**: System creates BM25 sparse index alongside vector embeddings
- [ ] **INDEX-03**: System ensures per-user index isolation via metadata filtering
- [ ] **INDEX-04**: System stores chunk metadata (doc_id, user_id, page_range, section) with embeddings
- [ ] **INDEX-05**: Re-ingesting same document (same hash) updates cleanly without duplication
- [ ] **INDEX-06**: OpenAI embedding model configured via environment (OPENAI_EMBEDDING_MODEL=text-embedding-3-small)

### Knowledge Graph (KG)

- [ ] **KG-01**: System extracts entities from chunks (services, APIs, components, configs, error types)
- [ ] **KG-02**: System extracts relationships between entities (depends_on, configures, connects_to)
- [ ] **KG-03**: System stores graph in FalkorDB (lightweight graph database with vector support)
- [ ] **KG-04**: System validates entity extraction quality (>70% accuracy threshold)
- [ ] **KG-05**: Graph-aware retrieval incorporates related entities for multi-component questions
- [ ] **KG-06**: Backend provides optional debug endpoint GET /api/debug/graph/sample for inspection

### Retrieval (RETRIEVAL)

- [ ] **RETRIEVAL-01**: System retrieves top-K chunks via txtai vector embeddings search (text-embedding-3-small)
- [ ] **RETRIEVAL-02**: System retrieves top-K chunks via BM25 keyword search
- [ ] **RETRIEVAL-03**: System fuses results using Reciprocal Rank Fusion (RRF)
- [ ] **RETRIEVAL-04**: System applies Mistral rerank model (via DeepInfra API) to fused results
- [ ] **RETRIEVAL-05**: Retrieval filters by user_id to isolate documents per user
- [ ] **RETRIEVAL-06**: System logs retrieval diagnostics (embedding scores, BM25 scores, RRF ranks, reranker scores)
- [ ] **RETRIEVAL-07**: Hybrid retrieval weights are configurable via environment (EMBED_WEIGHT, BM25_WEIGHT)
- [ ] **RETRIEVAL-08**: Mistral reranker configured via environment (RERANK_PROVIDER=deepinfra, RERANK_API_KEY)

### Chat & QA (CHAT)

- [ ] **CHAT-01**: User can ask natural language questions via IRONMIND interface
- [ ] **CHAT-02**: POST /api/chat endpoint accepts user_id, question, and optional history
- [ ] **CHAT-03**: System builds prompt with system message, retrieved context, and user question
- [ ] **CHAT-04**: System calls OpenAI GPT-5-mini API with constructed prompt
- [ ] **CHAT-05**: System returns answer with source citations (doc_id, filename, snippet, page_range)
- [ ] **CHAT-06**: Multi-source answers synthesize information across documents
- [ ] **CHAT-07**: System supports conversation history for multi-turn context
- [ ] **CHAT-08**: Query response time is under 10 seconds (target: 5-8 seconds)
- [ ] **CHAT-09**: System handles 2-3 concurrent users without degradation

### LLM Integration (LLM)

- [ ] **LLM-01**: Backend configures OpenAI GPT-5-mini via environment (LLM_PROVIDER=openai, LLM_MODEL=gpt-5-mini, LLM_API_KEY)
- [ ] **LLM-02**: System uses GPT-5-mini model for answer generation
- [ ] **LLM-03**: System includes retrieval context + conversation history in LLM prompt
- [ ] **LLM-04**: System enforces grounding instruction ("answer only from provided documents")

### Observability (OBS)

- [x] **OBS-01**: System logs structured JSON to stdout (timestamp, level, service, request_id, user_id)
- [x] **OBS-02**: Logging middleware generates unique request_id per request
- [x] **OBS-03**: System logs incoming requests (path, method, user_id)
- [x] **OBS-04**: System logs outgoing responses (status_code, duration)
- [ ] **OBS-05**: System logs key events (doc_ingestion_started, doc_ingestion_completed, rag_query_started, rag_query_completed, llm_call_started, llm_call_completed)
- [ ] **OBS-06**: System correlates log entries via request_id across pipeline stages
- [ ] **OBS-07**: System tracks and logs component latencies (docling-serve, txtai retrieval, Mistral reranking, GPT-5-mini)

### UI & UX (UI)

- [ ] **UI-01**: IRONMIND interface displays IAI branding with logo (IAI_logo_2025.jpg)
- [ ] **UI-02**: Landing page explains usage ("Upload up to 10 documents and chat with them")
- [ ] **UI-03**: Landing page includes POC disclaimer
- [ ] **UI-04**: Chat interface displays source citations with answers
- [ ] **UI-05**: Document list shows upload status per document
- [ ] **UI-06**: Error messages are user-friendly and actionable
- [ ] **UI-07**: IRONMIND branding consistent throughout (no LobeChat branding visible)

### Infrastructure (INFRA)

- [x] **INFRA-01**: Docker Compose orchestrates frontend, backend, docling-serve, FalkorDB, and txtai service
- [x] **INFRA-02**: Configuration via .env files (local vs cloud)
- [x] **INFRA-03**: Backend Dockerfile uses Python 3.11-slim (not Alpine)
- [ ] **INFRA-04**: System deploys to Hetzner VPS with HTTPS termination
- [x] **INFRA-05**: GET /health endpoint returns backend status
- [ ] **INFRA-06**: Frontend points to backend via environment-configurable base URL
- [x] **INFRA-07**: All secrets managed via environment variables (no hardcoding)
- [ ] **INFRA-08**: docling-serve deployed as separate service with API endpoint
- [ ] **INFRA-09**: FalkorDB deployed as graph database service
- [ ] **INFRA-10**: Hetzner API key configured for cloud deployment automation

### Documentation (DOCS)

- [ ] **DOCS-01**: README.md includes overview, features, tech stack, quickstart
- [ ] **DOCS-02**: docs/ARCHITECTURE.md describes components, data flow, RAG pipeline
- [ ] **DOCS-03**: docs/DEPLOYMENT.md provides local + cloud deployment instructions
- [ ] **DOCS-04**: docs/PIPELINE_DESIGN.md explains chunking strategy, embeddings, hybrid RAG, KG usage
- [ ] **DOCS-05**: docs/EXAMPLE_QUERIES.md provides 3+ Q&A examples with commentary
- [ ] **DOCS-06**: CONTRIBUTING.md outlines development guidelines
- [ ] **DOCS-07**: LICENSE file included (MIT)
- [ ] **DOCS-08**: Monorepo structure organized (/frontend, /backend, /infra, /docs)

## v2 Requirements

Deferred to future releases after Feb 1 deadline.

### Advanced Features

- **ADV-01**: Multi-modal RAG (images, diagrams from PDFs)
- **ADV-02**: Streaming LLM responses via Server-Sent Events (SSE)
- **ADV-03**: Advanced entity resolution for knowledge graph
- **ADV-04**: Multi-hop graph reasoning (2-3 hop traversal)
- **ADV-05**: Custom fine-tuned embeddings for aerospace domain
- **ADV-06**: Query intent classification

### Scalability

- **SCALE-01**: Multi-tenant support with tenant isolation
- **SCALE-02**: Distributed task queue for document processing
- **SCALE-03**: Caching layer (Redis) for frequent queries
- **SCALE-04**: Horizontal scaling for backend API
- **SCALE-05**: Support for >10 documents per user

### Observability

- **OBS-ADV-01**: Distributed tracing (Jaeger, OpenTelemetry)
- **OBS-ADV-02**: Metrics dashboard (Prometheus + Grafana)
- **OBS-ADV-03**: APM integration
- **OBS-ADV-04**: Query performance analytics

## Out of Scope

Explicitly excluded to maintain POC focus and Feb 1 timeline.

| Feature | Reason |
|---------|--------|
| Fine-tuning custom LLMs | High complexity, training data requirements, timeline risk |
| Multi-tenant SaaS | Single deployment sufficient for POC, adds auth/isolation complexity |
| Advanced authentication (SSO, OAuth, RBAC) | Email/password sufficient for assignment evaluation |
| Mobile applications | Web interface adequate, mobile dev doubles timeline |
| Real-time collaboration | Single-user sessions meet requirements |
| Video/audio document processing | Out of scope for text-based technical docs |
| Custom embeddings training | Use OpenAI embeddings for v1, domain tuning deferred |
| Production-scale infrastructure | POC scale (2-3 users, 10 docs) sufficient for assignment |
| Advanced security features | Basic auth + HTTPS adequate for demo, not handling classified data |
| Internationalization (i18n) | English-only documents, English UI sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| INGEST-01 | Phase 2 | Pending |
| INGEST-02 | Phase 2 | Pending |
| INGEST-03 | Phase 2 | Pending |
| INGEST-04 | Phase 2 | Pending |
| INGEST-05 | Phase 2 | Pending |
| INGEST-06 | Phase 2 | Pending |
| INGEST-07 | Phase 2 | Pending |
| INGEST-08 | Phase 2 | Pending |
| INGEST-09 | Phase 2 | Pending |
| INGEST-10 | Phase 2 | Pending |
| INDEX-01 | Phase 3 | Pending |
| INDEX-02 | Phase 3 | Pending |
| INDEX-03 | Phase 3 | Pending |
| INDEX-04 | Phase 3 | Pending |
| INDEX-05 | Phase 3 | Pending |
| INDEX-06 | Phase 3 | Pending |
| RETRIEVAL-01 | Phase 3 | Pending |
| RETRIEVAL-02 | Phase 3 | Pending |
| RETRIEVAL-03 | Phase 3 | Pending |
| RETRIEVAL-04 | Phase 3 | Pending |
| RETRIEVAL-05 | Phase 3 | Pending |
| RETRIEVAL-06 | Phase 3 | Pending |
| RETRIEVAL-07 | Phase 3 | Pending |
| RETRIEVAL-08 | Phase 3 | Pending |
| CHAT-01 | Phase 3 | Pending |
| CHAT-02 | Phase 3 | Pending |
| CHAT-03 | Phase 3 | Pending |
| CHAT-04 | Phase 3 | Pending |
| CHAT-05 | Phase 3 | Pending |
| CHAT-06 | Phase 3 | Pending |
| CHAT-07 | Phase 3 | Pending |
| CHAT-08 | Phase 3 | Pending |
| CHAT-09 | Phase 3 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| LLM-03 | Phase 3 | Pending |
| LLM-04 | Phase 3 | Pending |
| KG-01 | Phase 4 | Pending |
| KG-02 | Phase 4 | Pending |
| KG-03 | Phase 4 | Pending |
| KG-04 | Phase 4 | Pending |
| KG-05 | Phase 4 | Pending |
| KG-06 | Phase 4 | Pending |
| OBS-01 | Phase 1 | Complete |
| OBS-02 | Phase 1 | Complete |
| OBS-03 | Phase 1 | Complete |
| OBS-04 | Phase 1 | Complete |
| OBS-05 | Phase 2 | Pending |
| OBS-06 | Phase 3 | Pending |
| OBS-07 | Phase 3 | Pending |
| UI-01 | Phase 6 | Pending |
| UI-02 | Phase 6 | Pending |
| UI-03 | Phase 6 | Pending |
| UI-04 | Phase 6 | Pending |
| UI-05 | Phase 6 | Pending |
| UI-06 | Phase 6 | Pending |
| UI-07 | Phase 6 | Pending |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 6 | Pending |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 6 | Pending |
| INFRA-07 | Phase 1 | Complete |
| INFRA-08 | Phase 2 | Pending |
| INFRA-09 | Phase 4 | Pending |
| INFRA-10 | Phase 6 | Deferred |
| DOCS-01 | Phase 6 | Pending |
| DOCS-02 | Phase 6 | Pending |
| DOCS-03 | Phase 6 | Pending |
| DOCS-04 | Phase 6 | Pending |
| DOCS-05 | Phase 6 | Pending |
| DOCS-06 | Phase 6 | Pending |
| DOCS-07 | Phase 6 | Pending |
| DOCS-08 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 64 total
- Mapped to phases: 64 (100% coverage)
- Unmapped: 0 (no orphans)

**Phase Distribution:**
- Phase 1 (Infrastructure Foundation): 14 requirements
- Phase 2 (Document Processing Pipeline): 12 requirements
- Phase 3 (Core RAG with Hybrid Retrieval): 26 requirements
- Phase 4 (Knowledge Graph Integration): 6 requirements
- Phase 5 (Multi-Source Synthesis): 0 explicit requirements (enhances CHAT-06, CHAT-05)
- Phase 6 (Frontend Integration & Deployment): 15 requirements

**Notes:**
- Phase 5 has no explicit requirements but enhances multi-source synthesis capabilities (CHAT-06) and citation quality (CHAT-05)
- Phase 3 is the largest phase (26 requirements) covering indexing, retrieval, chat, and LLM integration as coherent RAG pipeline
- All authentication requirements front-loaded to Phase 1 for security-first approach

---
*Requirements defined: 2026-01-27*
*Last updated: 2026-01-27 after roadmap traceability mapping*
