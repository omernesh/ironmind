# Roadmap: IRONMIND - DocRAG POC for IAI

## Overview

IRONMIND delivers production-quality RAG capabilities for aerospace/defense technical documentation through six foundational phases. Starting with infrastructure and authentication (Phase 1), we build document processing foundation (Phase 2), establish core RAG with hybrid retrieval (Phase 3), integrate knowledge graph capabilities (Phase 4), enable multi-source synthesis (Phase 5), and complete with frontend integration and deployment (Phase 6). Each phase delivers verifiable capabilities with transparent traceability from answer to source, meeting defense industry standards for explainability and auditability within the 5-day February 1 deadline.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4, 5, 6): Planned milestone work
- Decimal phases (X.1, X.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Infrastructure Foundation** - Docker setup, auth, health checks, basic FastAPI structure
- [x] **Phase 2: Document Processing Pipeline** - Docling integration, semantic chunking, metadata preservation
- [x] **Phase 3: Core RAG with Hybrid Retrieval** - txtai indexing, BM25+semantic search, Qwen reranking, basic Q&A
- [x] **Phase 4: Knowledge Graph Integration** - FalkorDB setup, entity/relation extraction, graph-aware retrieval
- [ ] **Phase 5: Multi-Source Synthesis** - Cross-document reasoning, citation aggregation, synthesis prompting
- [ ] **Phase 6: Frontend Integration & Deployment** - IRONMIND UI, document upload, source traceability, Hetzner deployment

## Phase Details

### Phase 1: Infrastructure Foundation
**Goal**: Production-ready infrastructure with authentication, orchestration, and observability baseline
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, INFRA-01, INFRA-02, INFRA-03, INFRA-05, INFRA-07, INFRA-10, OBS-01, OBS-02, OBS-03, OBS-04
**Success Criteria** (what must be TRUE):
  1. User can register with email/password and log in via Better Auth
  2. User session persists across browser refresh
  3. Backend validates auth tokens and extracts user_id from authenticated requests
  4. Unauthenticated requests to protected endpoints return HTTP 401
  5. Docker Compose orchestrates all services (frontend, backend, docling-serve, FalkorDB)
  6. Backend logs structured JSON with request_id correlation across pipeline stages
  7. GET /health endpoint returns backend operational status
**Plans**: 5 plans in 4 waves

Plans:
- [x] 01-01-PLAN.md - Backend foundation with FastAPI, health endpoint, structured logging
- [x] 01-02-PLAN.md - Frontend Better Auth setup with login/register pages
- [x] 01-03-PLAN.md - Backend JWT validation middleware for protected endpoints
- [x] 01-04-PLAN.md - Docker Compose orchestration with environment configuration
- [x] 01-05-PLAN.md - Frontend-backend auth integration and end-to-end verification

### Phase 2: Document Processing Pipeline
**Goal**: High-quality document parsing with semantic chunking and structure preservation for accurate retrieval
**Depends on**: Phase 1
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, INGEST-08, INGEST-09, INGEST-10, INFRA-08, OBS-05
**Success Criteria** (what must be TRUE):
  1. User can upload DOCX/PDF documents (up to 10 per user) via backend API
  2. System successfully parses documents via docling-serve API preserving structure (sections, headings, page numbers)
  3. System applies semantic chunking (not fixed-size) with metadata (doc_id, filename, page_range, section_title, user_id)
  4. System stores original files to /data/raw/{user_id}/{doc_id} and processed output to /data/processed/{user_id}/{doc_id}
  5. Upload endpoint returns per-file status (Processing, Indexed, Failed)
  6. System logs doc_ingestion_started and doc_ingestion_completed events with durations
**Plans**: 5 plans (4 original + 1 gap closure)

Plans:
- [x] 02-01-PLAN.md - Storage layer with document models, database, and secure file storage
- [x] 02-02-PLAN.md - Document upload endpoint and docling-serve integration
- [x] 02-03-PLAN.md - Semantic chunking pipeline with txtai indexing
- [x] 02-04-PLAN.md - Status polling endpoint and end-to-end pipeline verification
- [x] 02-05-PLAN.md - [GAP CLOSURE] Fix docling output format mismatch for chunking

### Phase 3: Core RAG with Hybrid Retrieval
**Goal**: Working end-to-end RAG pipeline with hybrid retrieval (semantic + BM25) and Qwen3 reranking for technical document Q&A
**Depends on**: Phase 2
**Requirements**: INDEX-01, INDEX-02, INDEX-03, INDEX-04, INDEX-05, INDEX-06, RETRIEVAL-01, RETRIEVAL-02, RETRIEVAL-03, RETRIEVAL-04, RETRIEVAL-05, RETRIEVAL-06, RETRIEVAL-07, RETRIEVAL-08, CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, LLM-01, LLM-02, LLM-03, LLM-04, OBS-06, OBS-07
**Success Criteria** (what must be TRUE):
  1. System indexes chunks in txtai with OpenAI text-embedding-3-small embeddings and BM25 sparse index
  2. System retrieves top-K chunks via dual-channel search (txtai semantic + BM25) with Reciprocal Rank Fusion
  3. System applies Qwen3-Reranker model via DeepInfra API to fused results
  4. User can ask natural language questions and receive answers with source citations (doc_id, filename, snippet, page_range)
  5. System calls OpenAI GPT-5-mini for answer generation with grounding instruction
  6. Multi-source answers synthesize information across documents
  7. Query response time is under 10 seconds (target 5-8 seconds)
  8. System handles 2-3 concurrent users without degradation
  9. System logs retrieval diagnostics (embedding scores, BM25 scores, RRF ranks, reranker scores) and component latencies
**Plans**: 6 plans in 3 waves

Plans:
- [x] 03-01-PLAN.md - Configuration and chat data models for RAG pipeline
- [x] 03-02A-PLAN.md - Indexer hybrid search capability with OpenAI embeddings
- [x] 03-02B-PLAN.md - Hybrid retriever service with RRF fusion
- [x] 03-03-PLAN.md - Reranker service using DeepInfra Qwen3-Reranker
- [x] 03-04-PLAN.md - Answer generator with GPT-5-mini and citations
- [x] 03-05-PLAN.md - Chat endpoint with full pipeline orchestration

### Phase 4: Knowledge Graph Integration
**Goal**: Graph-aware retrieval enabling multi-component questions and relationship-based reasoning
**Depends on**: Phase 3
**Requirements**: KG-01, KG-02, KG-03, KG-04, KG-05, KG-06, INFRA-09
**Success Criteria** (what must be TRUE):
  1. System extracts entities (services, APIs, components, configs, error types) from chunks during ingestion
  2. System extracts relationships between entities (depends_on, configures, connects_to)
  3. System stores graph in FalkorDB with validated entity extraction quality (>70% accuracy threshold)
  4. Graph-aware retrieval incorporates related entities for multi-component questions
  5. Backend provides GET /api/debug/graph/sample endpoint for graph inspection
  6. System demonstrates improved answer quality for relationship-based queries (e.g., "how does X connect to Y")
**Plans**: 5 plans in 4 waves

Plans:
- [x] 04-01-PLAN.md - Graph schemas and FalkorDB client with configuration
- [x] 04-02-PLAN.md - LLM-based entity/relationship extraction with Structured Outputs
- [x] 04-03-PLAN.md - Pipeline integration for graph extraction during ingestion
- [x] 04-04-PLAN.md - Graph-aware dual-channel retrieval
- [x] 04-05-PLAN.md - Debug endpoint and end-to-end verification

### Phase 5: Multi-Source Synthesis
**Goal**: Advanced multi-document reasoning with cross-reference detection and comprehensive citation aggregation
**Depends on**: Phase 4
**Requirements**: (Implicitly supports CHAT-06 multi-source synthesis, enhances CHAT-05 citations)
**Success Criteria** (what must be TRUE):
  1. System detects explicit cross-references between documents (citations, hyperlinks, shared entity references)
  2. System builds document relationship graph tracking which docs reference which
  3. Answers to multi-document questions include citations from all relevant sources (3+ documents where applicable)
  4. System synthesizes information across documents with consistent entity resolution
  5. Response generation prioritizes graph-linked entities when building context for synthesis questions
**Plans**: 4 plans in 3 waves

Plans:

- [ ] 05-01-PLAN.md - Schema extensions and document relationship storage (Wave 1)
- [ ] 05-02-PLAN.md - Cross-reference detection and pipeline integration (Wave 2)
- [ ] 05-03-PLAN.md - Multi-source synthesis prompting in generator (Wave 2)
- [ ] 05-04-PLAN.md - Retrieval integration, debug endpoint, and verification (Wave 3)

### Phase 6: Frontend Integration & Deployment
**Goal**: Production-deployed IRONMIND interface with IAI branding, document management, and chat UX on Hetzner VPS
**Depends on**: Phase 5
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, INFRA-04, INFRA-06, DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07, DOCS-08
**Success Criteria** (what must be TRUE):
  1. IRONMIND interface displays IAI logo (IAI_logo_2025.jpg) with no LobeChat branding visible
  2. Landing page explains usage ("Upload up to 10 documents and chat with them") with POC disclaimer
  3. User can upload documents via UI and see status per document (Processing, Indexed, Failed)
  4. Chat interface displays answers with inline source citations (doc name, page, snippet)
  5. Error messages are user-friendly and actionable
  6. System deploys to Hetzner VPS with HTTPS termination
  7. Monorepo structure organized (/frontend, /backend, /infra, /docs) with complete documentation (README.md, ARCHITECTURE.md, DEPLOYMENT.md, PIPELINE_DESIGN.md, EXAMPLE_QUERIES.md, CONTRIBUTING.md, LICENSE)
**Plans**: TBD

Plans:
- [ ] 06-01: [Brief description - to be created during plan-phase]

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure Foundation | 5/5 | Complete | 2026-01-27 |
| 2. Document Processing Pipeline | 5/5 | Complete | 2026-01-28 |
| 3. Core RAG with Hybrid Retrieval | 6/6 | Complete | 2026-01-29 |
| 4. Knowledge Graph Integration | 5/5 | Complete | 2026-01-29 |
| 5. Multi-Source Synthesis | 0/4 | Not started | - |
| 6. Frontend Integration & Deployment | 0/TBD | Not started | - |
