# IRONMIND - DocRAG POC for IAI

## What This Is

IRONMIND is a production-quality RAG (Retrieval-Augmented Generation) proof-of-concept that enables authenticated users to upload aerospace/defense technical documents and interact with them through an intelligent chat interface. Built for an IAI (Israel Aerospace Industries) job assignment, the system demonstrates advanced RAG capabilities including FalkorDB knowledge graph integration, hybrid retrieval (semantic + keyword), Mistral reranking, and engineering-grade explainability with transparent source traceability.

## Core Value

Accurate, grounded answers from technical documentation with multi-source synthesis and transparent traceability from answer → source document → section. The system must extract non-trivial insights from highly technical aerospace/defense content, not just surface-level information retrieval.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Authentication & User Management**
- [ ] User registration and login via LobeChat's Better Auth (email/password)
- [ ] User identity available to backend for request tracking
- [ ] Authenticated-only access to ingestion and chat APIs

**Document Ingestion**
- [ ] Upload interface in LobeChat for DOCX/PDF documents
- [ ] Support for ~10 medium-sized documents per user (~20-40 pages each)
- [ ] Docling integration for document normalization and structure extraction
- [ ] Chunking with metadata preservation (section headings, page ranges, document IDs)
- [ ] txtai indexing with per-user isolation

**Knowledge Graph**
- [ ] Entity and relation extraction from technical documents (services, APIs, components, configs)
- [ ] Graph storage in txtai alongside embeddings
- [ ] Graph-aware retrieval for multi-component questions
- [ ] Optional debug endpoint for graph inspection

**Hybrid RAG**
- [ ] Dual retrieval: embedding-based + BM25 keyword search
- [ ] Configurable weighting between semantic and keyword results
- [ ] Rank fusion for final chunk selection
- [ ] Retrieval diagnostics logging (scores, sources, fusion results)

**Chat & Q&A**
- [ ] Natural language question interface via LobeChat
- [ ] RAG pipeline: retrieve → build prompt → LLM generation
- [ ] OpenAI GPT-4 integration with configurable model selection
- [ ] Response with answer + source citations (doc ID, filename, snippet, page range)
- [ ] Conversation history support

**Observability**
- [ ] Structured JSON logging to stdout (timestamp, level, service, request_id, user_id)
- [ ] Request/response logging with duration tracking
- [ ] Key event logging (ingestion_started, rag_query_completed, llm_call_completed)
- [ ] Correlation via request_id across log entries

**UI & UX**
- [ ] Professional LobeChat interface with project branding
- [ ] Document upload status display (Processing, Indexed, Failed)
- [ ] Source traceability in chat responses
- [ ] Clear POC disclaimer and usage instructions

**Deployment & Infrastructure**
- [ ] Docker Compose configuration for local and cloud deployment
- [ ] Hetzner/VPS cloud deployment with HTTPS
- [ ] Environment-driven configuration (12-factor)
- [ ] Health check endpoints

**Documentation** (Assignment Deliverables)
- [ ] Professional GitHub monorepo structure (/frontend, /backend, /infra, /docs)
- [ ] README.md with overview, architecture, quickstart
- [ ] docs/ARCHITECTURE.md - components, data flow, RAG pipeline
- [ ] docs/DEPLOYMENT.md - local + cloud deployment instructions
- [ ] docs/PIPELINE_DESIGN.md - chunking strategy, embeddings, hybrid RAG, KG usage
- [ ] docs/EXAMPLE_QUERIES.md - 3+ Q&A examples with commentary
- [ ] CONTRIBUTING.md - development guidelines
- [ ] LICENSE (MIT)

### Out of Scope

- Multi-tenant SaaS features — Single deployment, 2-3 concurrent users maximum
- Advanced authentication (SSO, OAuth, RBAC) — Basic email/password sufficient for POC
- Heavy observability stack (Jaeger, APM, distributed tracing) — Structured logs only
- Production-scale optimization — POC scale (~10 documents, not large corpora)
- Real-time collaboration features — Single-user chat sessions
- Mobile applications — Web-only interface via LobeChat
- Fine-tuning or custom models — Using OpenAI GPT-4 as-is

## Context

**Assignment Background:**
- Job application assignment for IAI (Israel Aerospace Industries) - Domain AI Lead position
- Evaluation criteria: accuracy of answers, multi-source synthesis, insight extraction from technical text
- Emphasis on "engineering-grade AI" with explainability, not "ChatGPT cosplay"
- Defense industry values: determinism, auditability, traceability, extensibility

**Technical Documents:**
- 10 aerospace/defense technical documents (DOC/DOCX format)
- Highly technical content: configurations, services, flows, system specifications
- English language, ~10MB total corpus
- File names suggest system documentation (FC-*, D*, B-* codes)

**Prior Research:**
- ChatGPT feedback validated approach: hybrid RAG + knowledge graph is strong for this use case
- txtai chosen for lightweight, native hybrid search support
- Docling chosen for aerospace/defense document structure preservation
- FalkorDB initially considered but txtai's built-in KG support preferred for simplicity

**Expected Performance:**
- Query response time: 5-8 seconds including retrieval + LLM generation
- Concurrent users: 2-3 maximum
- Deployment target: Single small VPS (Hetzner CX21/CX31 equivalent)

## Constraints

- **Timeline**: Deadline February 1, 2026 (Sunday) - approximately 5 days from project start
- **Scale**: POC only - maximum 10 documents per user, 2-3 concurrent users
- **Tech Stack**: Python (FastAPI backend), LobeChat (frontend with IRONMIND branding), txtai (RAG), docling-serve (doc processing API), FalkorDB (knowledge graph)
- **LLM Provider**: OpenAI GPT-5-mini (configurable via environment variables)
- **Embeddings**: OpenAI text-embedding-3-small
- **Reranking**: Mistral rerank model via DeepInfra API
- **Email Provider**: Mailgun SMTP for Better Auth email verification/password reset
- **Domain**: ironmind.chat (owned, for deployment)
- **Deployment Target**: Hetzner VPS with Docker Compose orchestration, HTTPS at ironmind.chat
- **Budget**: POC-appropriate - avoid expensive infrastructure or API costs during development
- **Security**: HTTPS termination at deployment level, no open anonymous APIs, basic authentication only
- **Branding**: IRONMIND branding throughout, IAI logo (IAI_logo_2025.jpg), no LobeChat/Claude references visible

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| txtai for RAG backend | Lightweight, native hybrid search, embeddings management, easier to reason about than LangChain | — Pending |
| FalkorDB for knowledge graph | Lighter and more flexible than Neo4j, vector + graph in single DB, good for POC scale | — Pending |
| docling-serve API | Separate service for document processing, better separation of concerns than embedded Docling library | — Pending |
| OpenAI text-embedding-3-small | Cost-effective, high-quality embeddings for technical content, well-tested | — Pending |
| Mistral rerank (DeepInfra) | 30-50% precision boost via reranking, API-based avoids local model hosting complexity | — Pending |
| Hybrid RAG (BM25 + embeddings) | Technical docs require exact term matching (IDs, configs, parameters) alongside semantic understanding | — Pending |
| LobeChat frontend with IRONMIND branding | Professional UI out-of-box, Better Auth built-in, rebrand to remove LobeChat references | — Pending |
| OpenAI GPT-5-mini | Latest model, faster and cheaper than GPT-4 while maintaining quality for grounded Q&A | — Pending |
| Mailgun SMTP | Better Auth email verification/password reset, reliable email delivery, straightforward API | — Pending |
| ironmind.chat domain | Professional domain for deployment, branded URL for assignment submission | — Pending |
| Hetzner VPS | European infrastructure, cost-effective, straightforward deployment, API for automation | — Pending |
| Monorepo structure | Professional presentation for GitHub submission, clear organization for reviewers | — Pending |

---
*Last updated: 2026-01-27 after initialization*
