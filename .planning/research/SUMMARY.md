# Project Research Summary

**Project:** DocRAG POC - RAG System with Knowledge Graph + Hybrid Retrieval
**Domain:** Technical Document Q&A for Defense/Aerospace
**Researched:** 2026-01-27
**Confidence:** HIGH

## Executive Summary

This is a production-grade RAG system for aerospace/defense technical documentation requiring explainability, auditability, and multi-document synthesis. Based on extensive research, the recommended approach leverages txtai 9.4.1 as an all-in-one RAG orchestration framework with built-in hybrid retrieval (BM25 + semantic vectors), Docling 2.70.0 for document processing, and OpenAI GPT-4 for generation. The architecture separates ingestion (document processing, chunking, indexing) from query pipelines (hybrid retrieval, knowledge graph traversal, response generation), deployed via Docker Compose on a single VPS for POC scale.

The critical success factors are: (1) semantic chunking that preserves document structure and metadata for source attribution, (2) hybrid retrieval with Reciprocal Rank Fusion to handle both conceptual and exact-match queries, (3) knowledge graph integration for multi-hop reasoning across documents, and (4) structured logging for engineering-grade observability. The 5-day timeline is feasible if the architecture is planned upfront, evaluation harnesses are built early (Day 2), and risky features like knowledge graph extraction are validated on small document sets before scaling.

The primary risks are: context fragmentation from poor chunking (mitigate with semantic boundaries and metadata preservation), knowledge graph extraction quality (validate on 2-3 documents first), and timeline pressure leading to monolithic architecture (enforce modular separation from Day 1). Research indicates hybrid retrieval is table stakes for technical documents (15-30% better recall than single-method), source attribution is non-negotiable for defense contexts, and entity resolution is the biggest knowledge graph pitfall (30-40% wrong relationships without proper disambiguation).

## Key Findings

### Recommended Stack

The stack prioritizes speed-to-production with battle-tested components while meeting enterprise requirements. txtai provides a unified embeddings database combining vector search, BM25, and knowledge graph storage, eliminating the need for separate vector databases or graph systems at POC scale. Docling excels at parsing technical PDFs with complex tables and structure preservation. FastAPI provides async request handling for streaming responses, while LobeChat offers a production-ready chat interface with native authentication and file upload capabilities.

**Core technologies:**
- **txtai 9.4.1**: All-in-one RAG orchestration (embeddings, BM25, graph storage, LLM integration) — eliminates integration complexity, production-ready, latest release Jan 2026
- **Docling 2.70.0**: Document processing for PDF/DOCX with structure preservation — IBM-backed, superior table extraction, reading order detection for technical docs
- **FastAPI**: REST API framework with async support — industry standard for AI APIs, native OpenAPI docs, strong observability ecosystem
- **OpenAI GPT-4**: LLM for generation — best-in-class performance, txtai integrates via LiteLLM for unified API
- **Python 3.11-slim**: Runtime and base Docker image — Docling requires 3.10+, slim images 50x faster than Alpine
- **Sentence Transformers (bge-large-en-v1.5)**: Dense embeddings — state-of-the-art for technical document retrieval with proper prefix handling
- **Neo4j 6.1 (optional)**: Dedicated graph database if txtai's built-in graph insufficient — mature Python driver, GraphRAG package available
- **structlog**: Structured JSON logging — production-grade observability, essential for defense industry auditability
- **Docker Compose**: Multi-container orchestration — sufficient for POC scale, simpler than Kubernetes

**Version constraints:**
- Python 3.11 minimum (Docling 2.70+ dropped 3.9 support)
- Never use Alpine base images (50x slower builds, musl libc issues)
- txtai 9.4.1 or later (fixes httpx import bug)
- Neo4j driver package is `neo4j` not `neo4j-driver` (deprecated since 6.0)

### Expected Features

Research reveals three tiers: table stakes that must be present or the system feels incomplete, differentiators that provide competitive advantage, and anti-features that create scope creep.

**Must have (table stakes):**
- Source citations with document ID, filename, page range, and text snippet — RAG without citations is a "black box"
- Semantic vector search — baseline RAG capability, txtai provides out-of-box
- Keyword/exact match search (BM25) — technical docs contain IDs, codes, parameters requiring exact matches
- Multi-document retrieval — answers must synthesize across sources, not just single doc
- Document structure preservation — headers, sections, tables preserved for context (Docling integration)
- Conversation history — follow-up questions reference previous context (LobeChat provides)
- Upload status feedback — Processing/Indexed/Failed states prevent user confusion
- Response latency under 10 seconds — industry standard for RAG Q&A (5-8s target)
- Structured JSON logging — engineering-grade systems require debuggability (timestamp, request_id, user_id)
- Authentication/access control — LobeChat Better Auth provides this

**Should have (competitive advantage):**
- Knowledge graph entity relationships — enables "how does service X connect to config Y" questions that pure vector search misses
- Hybrid retrieval with Rank Fusion (RRF) — combines semantic + keyword intelligently, 15-30% precision improvement
- Reranking with cross-encoder — 30-50% precision boost over basic similarity (defer to v1.x if timeline tight)
- Explainable retrieval pipeline — shows semantic score, BM25 score, fusion rank for debugging
- Semantic chunking strategy — chunks respect document structure (section boundaries) vs arbitrary splits, reduces 60% boundary errors
- Context window optimization — retrieve adjacent chunks within same section to improve coherence
- Audit trail for compliance — cryptographic chain of custody for retrieval-generation-response (defer to v2+ but flag requirement)
- Document metadata filtering — "search only configuration docs" or "exclude appendices"

**Defer (v2+ or anti-features):**
- Real-time collaborative editing — massive complexity, not core to RAG value
- Fine-tuned custom LLM — timeline killer, GPT-4 already excellent at technical text
- Multi-tenant SaaS infrastructure — POC is 2-3 users, overengineering
- Advanced RBAC beyond basic auth — scope creep, not evaluation criteria
- Streaming LLM responses — adds complexity for marginal UX gain at 5-8s response times
- Document versioning — complicates indexing and storage
- Custom NER for entity extraction — use txtai's LLM-driven extraction or rule-based
- Multi-modal RAG (images/diagrams) — high risk for 5-day timeline
- Real-time document monitoring — unnecessary for static upload workflow
- Query auto-completion — low value vs effort for technical users

### Architecture Approach

The architecture follows modular RAG patterns with clear separation between ingestion and query pipelines, avoiding monolithic scripts that are hard to test and iterate. txtai serves as the unified storage layer (vectors, BM25 index, graph), eliminating the need for separate databases at POC scale. Document processing uses Docling for structure-aware parsing, followed by semantic chunking that preserves metadata. Hybrid retrieval executes parallel BM25 and vector searches, merges results with Reciprocal Rank Fusion, and optionally enhances context via knowledge graph traversal. Response generation uses async streaming with inline citation injection.

**Major components:**
1. **LobeChat Frontend** — User interface with auth, document upload, chat interaction (Next.js with Better Auth)
2. **FastAPI Backend** — API routing, validation, authentication enforcement, RAG orchestration (async Python)
3. **Document Processor** — Parse documents (Docling), extract structure, semantic chunking with metadata preservation
4. **Hybrid Retriever** — Dual-channel retrieval (txtai semantic + BM25), Reciprocal Rank Fusion for score merging
5. **txtai Embeddings Database** — Unified storage for vectors, BM25 index, knowledge graph, and metadata
6. **Knowledge Graph Builder** — Entity/relation extraction (txtai Labels pipeline or pattern-based), graph storage in txtai
7. **Response Generator** — Context-aware prompt building, GPT-4 invocation via LiteLLM, streaming with citations
8. **Observability Layer** — structlog with JSON output, request correlation IDs, performance metrics

**Key architectural patterns:**
- Dual-channel hybrid retrieval with RRF fusion (Pattern 1) — parallel BM25 + semantic, merge with reciprocal rank
- Structured document ingestion with metadata preservation (Pattern 2) — Docling parsing, semantic chunking, rich metadata
- Async streaming response with citation injection (Pattern 3) — FastAPI SSE, token streaming, inline sources
- Knowledge graph integration for multi-hop retrieval (Pattern 4) — entity extraction, graph storage, graph-aware queries

**Project structure:**
```
docrag-poc/
├── frontend/          # LobeChat deployment
├── backend/
│   ├── app/
│   │   ├── api/       # ingestion.py, chat.py, health.py
│   │   ├── services/  # document_processor.py, retriever.py, graph_builder.py, generator.py
│   │   ├── models/    # Pydantic request/response schemas
│   │   └── core/      # config.py, logging.py, auth.py
├── infra/             # docker-compose.yml
└── docs/              # ARCHITECTURE.md, PIPELINE_DESIGN.md
```

**Data flows:**
- Ingestion: Upload → Docling parse → semantic chunking → entity extraction → txtai indexing (embeddings + BM25 + graph)
- Query: Query → hybrid retrieval (parallel BM25 + semantic) → RRF fusion → graph enhancement → prompt building → GPT-4 streaming → citation injection

**Deployment:**
Docker Compose on single VPS (Hetzner CX21/CX31) with volume mounts for txtai index persistence. Frontend (LobeChat) on port 3000, backend (FastAPI) on port 8000, optional Nginx for HTTPS termination.

### Critical Pitfalls

Research identified seven critical pitfalls ranked by likelihood and impact for this project:

1. **Context fragmentation through poor chunking** — Fixed-size chunking splits tables from context, breaks sentence boundaries, loses structural metadata. Technical documents require semantic chunking respecting sections, with metadata preservation (section headers, page numbers). **Prevention:** Use Docling's structure detection, chunk at section boundaries, validate 20-30 chunks manually before full processing. **Phase 1 must-have.**

2. **Inadequate source attribution** — Answers without explicit citations to doc ID, page, section are unusable in defense contexts. Metadata gets stripped during embedding or isn't propagated through retrieval-generation pipeline. **Prevention:** Store rich metadata with every chunk (`{doc_id, doc_title, section, page}`), format LLM responses with inline citations, add citation coverage metric to evaluation. **Phase 2 architecture requirement.**

3. **Hybrid retrieval tuning without baseline measurements** — Arbitrary BM25/semantic weights (0.5/0.5) without testing individual components causes suboptimal performance. **Prevention:** Establish baselines (BM25-only, semantic-only) on 30-50 queries FIRST, use RRF (no tuning needed) initially, measure precision@k and recall@k independently. **Phase 3 critical validation.**

4. **Knowledge graph extraction without quality validation** — LLM extraction produces 30-40% incorrect edges (duplicate entities, wrong relationships, hallucinated connections). **Prevention:** Start with 2-3 documents, manually verify before scaling, implement entity resolution (canonical forms), track extraction confidence scores, build 50-100 verified triples for regression testing. **Phase 4 validation gate.**

5. **Docling failures handled silently** — Complex PDFs cause hangs, scanned documents return partial/empty results, tables with merged cells produce garbled output. **Prevention:** Test Docling on representative documents Day 1 (scanned pages, complex tables), implement timeouts (120s) and fallbacks, validate extraction quality (page counts, table cell counts, OCR confidence), have alternative parser ready (Unstructured.io). **Phase 1 Day 1 requirement.**

6. **Multi-document synthesis without cross-reference detection** — System retrieves from multiple docs but misses explicit references (citations) or implicit relationships (shared entities). **Prevention:** Extract cross-references during processing, build document relationship graph, implement graph-based entity linking, add relationship metadata to chunks. **Phase 5 enhancement.**

7. **5-day timeline pressure leading to architectural shortcuts** — Monolithic scripts, no evaluation harness, no caching, skipped tests. **Prevention:** Day 1 architecture sketch (separate ingestion/query pipelines), semantic caching from start, build minimal eval harness (30 Q&A pairs) on Day 2, modular design for independent testing, timebox knowledge graph to 1 day max. **Phase 0 planning critical.**

**Additional gotchas:**
- txtai + Docling integration: Don't feed raw Markdown directly, preserve structure metadata
- Context window management: Rank chunks, take top-k fitting 70% of limit, reserve 30% for generation
- User isolation: Filter by user_id metadata, don't create per-user indexes (doesn't scale)
- No reranking after RRF wastes context window on low-quality chunks (add for v1.x)

## Implications for Roadmap

Based on research findings, suggested 6-phase structure with rationale:

### Phase 1: Document Processing Foundation
**Rationale:** Chunking quality determines retrieval ceiling — must get right before building retrieval. Docling validation required Day 1 to avoid discovering issues on Day 4.

**Delivers:**
- Docling integration tested on all target documents (10 PDFs)
- Semantic chunking respecting document structure (sections, tables)
- Metadata preservation pipeline (doc_id, filename, section, page, chunk_index)
- Chunk quality validation (manual inspection of 20-30 samples)

**Addresses Features:**
- Document structure preservation (table stakes)
- Source attribution foundation (metadata in chunks)

**Avoids Pitfalls:**
- Pitfall 1: Context fragmentation (semantic chunking)
- Pitfall 5: Docling failures (validation Day 1)

**Research Flag:** Low — Docling well-documented, chunking patterns established. Standard implementation.

### Phase 2: Core RAG Pipeline
**Rationale:** Establish baseline RAG capability before adding hybrid complexity. Build evaluation harness early to measure improvements in later phases.

**Delivers:**
- txtai embeddings database with semantic vector search
- Basic retrieval endpoint (top-k semantic search)
- Minimal evaluation harness (30-50 Q&A pairs with expected sources)
- FastAPI basic endpoints (/ingest, /query, /health)
- Structured logging with request correlation IDs

**Uses Stack:**
- txtai 9.4.1 (semantic search)
- Sentence Transformers (bge-large-en-v1.5)
- FastAPI + structlog
- OpenAI GPT-4 via LiteLLM

**Implements Architecture:**
- Document Processor component
- txtai Embeddings Database component
- Response Generator component (basic)

**Avoids Pitfalls:**
- Pitfall 2: Source attribution built into architecture (metadata propagation)
- Pitfall 7: Evaluation harness prevents "looks done but isn't"

**Research Flag:** Low — Standard RAG pipeline, txtai examples available (50+).

### Phase 3: Hybrid Retrieval Integration
**Rationale:** Hybrid retrieval is table stakes for technical documents (exact matches + semantic). Must baseline each method independently before fusion.

**Delivers:**
- BM25 keyword search integration in txtai (enable `hybrid=True`)
- Reciprocal Rank Fusion implementation for score merging
- Baseline measurements (BM25-only, semantic-only, hybrid) on eval set
- Hybrid retrieval evaluation showing 15-30% improvement over single-method

**Uses Stack:**
- txtai native BM25 implementation
- RRF algorithm (no tuning needed)

**Implements Architecture:**
- Hybrid Retriever component (Pattern 1)

**Avoids Pitfalls:**
- Pitfall 3: Baseline measurements before optimization (precision@k, recall@k)

**Research Flag:** Low — RRF well-documented, txtai hybrid mode native. Measure, don't over-tune.

### Phase 4: Knowledge Graph Integration
**Rationale:** Differentiator feature for assignment evaluation (multi-hop reasoning, relationship-aware retrieval). High risk — validate extraction quality on small set before scaling.

**Delivers:**
- Entity extraction pipeline (txtai Labels or pattern-based)
- Relationship extraction for technical entities (services, components, configs)
- txtai graph storage integration
- Knowledge graph validation on 2-3 documents (50-100 verified triples)
- Graph-aware retrieval enhancement (optional: only if KG adds value)

**Uses Stack:**
- txtai semantic graph (built-in)
- txtai Labels pipeline for entity extraction
- Optional: Neo4j 6.1 if txtai graph insufficient

**Implements Architecture:**
- Knowledge Graph Builder component
- Graph-aware retrieval in Hybrid Retriever

**Avoids Pitfalls:**
- Pitfall 4: Quality validation before scaling (manual verification gate)
- Pitfall 7: Timebox to 1 day max, skip if not adding value

**Research Flag:** MEDIUM — Entity extraction quality depends on document domain. Validate with 2-3 samples before committing.

**De-scope trigger:** If KG extraction quality < 70% correct after 4 hours, defer to post-POC and focus on hybrid retrieval excellence.

### Phase 5: Multi-Source Synthesis Enhancement
**Rationale:** Assignment requires synthesis across documents. Cross-reference detection improves answer completeness for inter-document dependencies.

**Delivers:**
- Cross-reference extraction (explicit citations, hyperlinks between docs)
- Document relationship graph (which docs reference which)
- Multi-document retrieval with relationship awareness
- Graph-based entity linking across documents

**Addresses Features:**
- Multi-document retrieval (table stakes)
- Context window optimization (competitive advantage)

**Avoids Pitfalls:**
- Pitfall 6: Cross-reference detection prevents missing inter-document constraints

**Research Flag:** MEDIUM — Cross-reference patterns vary by document type. May need custom extraction logic for defense docs.

### Phase 6: Frontend Integration & Polish
**Rationale:** LobeChat integration tested incrementally Days 2-5, final day for end-to-end polish and documentation.

**Delivers:**
- LobeChat frontend deployed with backend API integration
- Authentication via LobeChat Better Auth
- Document upload UI with status tracking
- Chat interface with conversation history and source citations
- Docker Compose orchestration (frontend + backend)
- Documentation (ARCHITECTURE.md, deployment guide, example queries)

**Uses Stack:**
- LobeChat (Next.js)
- LobeChat Better Auth
- Docker Compose

**Implements Architecture:**
- LobeChat Frontend component
- Docker Compose deployment architecture

**Research Flag:** MEDIUM — LobeChat-txtai integration pattern less documented, test early.

### Phase Ordering Rationale

1. **Foundation-first approach:** Document processing quality (Phase 1) determines retrieval ceiling — must be solid before building on it
2. **Baseline before optimization:** Core RAG (Phase 2) + evaluation harness establishes baseline, enables measuring improvements from hybrid (Phase 3) and graph (Phase 4)
3. **Risk isolation:** Knowledge graph (Phase 4) timeboxed with de-scope trigger — if extraction quality poor, still have excellent hybrid retrieval
4. **Incremental validation:** Each phase has clear deliverable and validation criteria, can proceed or pivot based on results
5. **Dependency ordering:** Multi-source synthesis (Phase 5) requires working KG (Phase 4), frontend (Phase 6) requires all backend components operational

### Research Flags

**Phases needing deeper research during planning:**

- **Phase 4 (Knowledge Graph):** Entity extraction quality highly domain-dependent. Need to validate extraction patterns on actual aerospace/defense documents. Recommend `/gsd:research-phase` focused on: entity types for technical docs, relationship patterns, extraction confidence thresholds.

- **Phase 5 (Multi-Source Synthesis):** Cross-reference extraction patterns vary by document type. May need custom logic for defense technical docs (standard citations, specification references). Research needed on: cross-reference regex patterns, document relationship schemas.

- **Phase 6 (LobeChat Integration):** LobeChat-backend integration less documented (Medium confidence). Test early with simple endpoints. Research if needed: LobeChat API expectations, Better Auth token format, file upload handling.

**Phases with standard patterns (skip research-phase):**

- **Phase 1 (Document Processing):** Docling well-documented with examples, chunking strategies researched. Standard implementation.

- **Phase 2 (Core RAG):** txtai has 50+ examples, basic RAG pattern established. Standard implementation.

- **Phase 3 (Hybrid Retrieval):** txtai native BM25, RRF algorithm standard. Measurement protocol clear from research.

### Timeline Risk Mitigation

**Critical path:** Phase 1 (24% of timeline) is highest risk — Docling issues discovered late would cascade. Mitigation: Test Docling on all target documents Day 1 Hour 1-2, have fallback parser (Unstructured.io) ready.

**De-scoping priorities if behind schedule:**
1. **Keep:** Document processing quality (Phase 1), source attribution (Phase 2), evaluation harness (Phase 2), core RAG (Phase 2)
2. **Simplify:** Use semantic-only or BM25-only instead of hybrid (Phase 3 becomes quick comparison instead of full integration)
3. **Skip if needed:** Knowledge graph (Phase 4) has highest risk/reward ratio — excellent hybrid RAG without graph still demonstrates capability

**Day-by-day allocation:**
- Day 1: Phase 1 (Document Processing Foundation) — validate Docling, implement semantic chunking
- Day 2: Phase 2 (Core RAG Pipeline) — txtai semantic search, evaluation harness, basic endpoints
- Day 3: Phase 3 (Hybrid Retrieval) — BM25 integration, RRF fusion, baseline measurements
- Day 4: Phase 4 (Knowledge Graph) — entity extraction (validate quality gate), graph storage, OR skip to Phase 5 if KG validation fails
- Day 5: Phase 5 + 6 (Multi-Source + Frontend) — cross-references, LobeChat integration, polish, documentation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | txtai 9.4.1, Docling 2.70.0, FastAPI, Python 3.11 verified from official PyPI, GitHub releases (Jan 2026). Version compatibility matrix confirmed. Docker best practices from authoritative sources. |
| Features | **MEDIUM-HIGH** | Table stakes features verified from multiple 2026 sources (hybrid retrieval standard, source attribution requirement). Knowledge graph ROI claims from credible sources but single-source (11% improvement). Reranking performance (30-50%) from multiple guides. |
| Architecture | **HIGH** | Hybrid retrieval patterns documented in production implementations (NetApp, Redis, OpenSearch guides). FastAPI async patterns standard. txtai architecture well-documented with examples. Docker Compose deployment pattern established. |
| Pitfalls | **MEDIUM-HIGH** | Chunking fragmentation documented in multiple 2026 technical sources with 60% error reduction claims. Docling failure modes from comparative benchmarks. Knowledge graph extraction quality (30-40% error rate) from academic paper (single source). Hybrid tuning issues from production guides. |

**Overall confidence:** **HIGH**

Research based on:
- Primary sources (HIGH confidence): Official documentation (txtai, Docling, Neo4j, FastAPI), PyPI version verification, GitHub release notes dated Jan 2026
- Secondary sources (MEDIUM confidence): Production implementation guides (2026-dated), technical blog posts from credible vendors (Redis, NetApp, Microsoft), comparative benchmarks
- Tertiary sources (LOW confidence, flagged): Single-source performance claims (knowledge graph 11% improvement, semantic chunking 60% error reduction) — needs validation during implementation

### Gaps to Address

**Knowledge graph extraction quality** — Research shows 30-40% incorrect edges without entity resolution, but actual rate depends on document domain and extraction method. Validation needed on aerospace/defense technical documents specifically. **Handle:** Phase 4 validation gate — manually verify 50-100 triples from 2-3 documents before scaling. If quality < 70% correct, defer KG to post-POC.

**LobeChat-backend integration pattern** — LobeChat documentation covers general usage, but specific integration with custom RAG backend less documented. API contract assumptions unclear. **Handle:** Test simple endpoints Day 2, validate file upload and auth token handling. If integration issues arise, consider alternative frontend (Open WebUI, custom Next.js).

**Docling performance on aerospace/defense documents** — Benchmarks show Docling excels on academic PDFs and general technical docs, but specific performance on defense specifications (scanned pages, hand-annotated, complex classification markings) unknown. **Handle:** Test on representative sample documents Day 1. If extraction quality poor (< 80% accuracy on tables), switch to fallback parser (Unstructured.io, LlamaParse).

**Semantic chunking optimal parameters for technical docs** — Research establishes semantic chunking superiority over fixed-size, but optimal chunk size (512 vs 1024 tokens) and overlap (50 vs 100 tokens) domain-dependent. **Handle:** Test 2-3 configurations on eval set during Phase 2, measure retrieval precision. Use 512 tokens / 50 token overlap as starting point (standard for technical docs).

**Hybrid retrieval weight tuning necessity** — Research recommends RRF (no tuning), but some sources suggest weighted combination performs better for domain-specific queries. **Handle:** Start with RRF in Phase 3. If baseline measurements show one method significantly dominates (> 80% of top-5 results), consider weighted combination. Otherwise, RRF sufficient for POC.

**Multi-hop reasoning performance via knowledge graph** — Research claims graph enables multi-hop questions but doesn't quantify accuracy improvement or specify hop depth limits. **Handle:** Design eval queries with explicit 1-hop and 2-hop questions during Phase 4. Measure answer accuracy with/without graph enhancement. If < 10% improvement, flag as post-POC enhancement rather than core feature.

## Sources

### Primary Sources (HIGH Confidence)

**Stack verification:**
- [txtai PyPI 9.4.1](https://pypi.org/project/txtai/) — Official package, Jan 23 2026 release
- [txtai GitHub Releases](https://github.com/neuml/txtai/releases) — Release notes, hybrid search in 6.0+
- [Docling PyPI 2.70.0](https://pypi.org/project/docling/) — Official package, Jan 23 2026 release, Python 3.10+ requirement
- [Neo4j Python Driver 6.1](https://neo4j.com/docs/api/python-driver/current/) — Official API documentation
- [Python Docker Alpine Issues](https://pythonspeed.com/articles/alpine-docker-python/) — Authoritative performance analysis (50x build time)
- [txtai Hybrid Search Announcement](https://medium.com/neuml/whats-new-in-txtai-6-0-7d93eeedf804) — Direct from maintainer

**Architecture patterns:**
- [txtai Embeddings Documentation](https://neuml.github.io/txtai/embeddings/) — Official architecture reference
- [txtai Semantic Graphs Examples](https://github.com/neuml/txtai/blob/master/examples/38_Introducing_the_Semantic_Graph.ipynb) — Official KG integration
- [FastAPI Observability Stack](https://github.com/blueswen/fastapi-observability) — Production observability patterns

### Secondary Sources (MEDIUM Confidence)

**Hybrid retrieval best practices:**
- [Understanding Hybrid Search RAG](https://www.meilisearch.com/blog/hybrid-search-rag) — 2026 industry guide
- [Hybrid RAG in the Real World](https://community.netapp.com/t5/Tech-ONTAP-Blogs/Hybrid-RAG-in-the-Real-World-Graphs-BM25-and-the-End-of-Black-Box-Retrieval/ba-p/464834) — NetApp production implementation
- [Optimizing RAG with Hybrid Search & Reranking](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking) — Performance benchmarks
- [RAG in 2026: Practical Blueprint](https://dev.to/suraj_khaitan_f893c243958/-rag-in-2026-a-practical-blueprint-for-retrieval-augmented-generation-16pp) — Reranking 30-50% improvement claim

**Knowledge graph integration:**
- [Towards Practical GraphRAG](https://arxiv.org/html/2507.03226v3) — Academic research on KG construction
- [HybridRAG: Integrating Knowledge Graphs and Vector Retrieval](https://arxiv.org/html/2408.04948v1) — 11% relevance improvement claim
- [Neo4j GraphRAG for Python](https://neo4j.com/blog/developer/knowledge-graphs-neo4j-graphrag-for-python/) — Official Neo4j integration guide
- [DeepLearning.AI Knowledge Graphs for RAG](https://www.deeplearning.ai/short-courses/knowledge-graphs-rag/) — Educational resource

**Document processing & chunking:**
- [Chunking Strategies for RAG](https://weaviate.io/blog/chunking-strategies-for-rag) — Industry comparison
- [Ultimate Guide to Chunking - Databricks](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089) — Production patterns
- [Semantic Boundaries Cut RAG Errors 60%](https://ragaboutit.com/the-chunking-strategy-shift-why-semantic-boundaries-cut-your-rag-errors-by-60/) — Performance claim
- [PDF Table Extraction Showdown](https://boringbot.substack.com/p/pdf-table-extraction-showdown-docling) — Docling vs alternatives benchmark

**Citation & traceability:**
- [Effective Source Tracking in RAG](https://www.chitika.com/source-tracking-rag/) — Implementation patterns
- [FINOS Citations & Source Traceability](https://air-governance-framework.finos.org/mitigations/mi-13_providing-citations-and-source-traceability-for-ai-generated-information.html) — Financial industry standards
- [Building Trustworthy RAG with Citations](https://haruiz.github.io/blog/improve-rag-systems-reliability-with-citations) — Best practices guide

**Pitfalls & anti-patterns:**
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them) — Comprehensive pitfall catalog
- [Why Your RAG System Fails on Technical Documents](https://medium.com/@officialchiragp1605/why-your-rag-system-fails-on-technical-documents-and-how-to-fix-it-5c9e5be7948f) — Domain-specific failures
- [Diagnosing and Addressing Pitfalls in KG-RAG](https://openreview.net/pdf?id=Vd5JXiX073) — Knowledge graph quality issues
- [RAG at Scale: How to Build Production AI Systems in 2026](https://redis.io/blog/rag-at-scale/) — Scaling considerations

**Production architecture:**
- [Building Production-Grade RAG Systems](https://medium.com/@kranthigoud975/building-production-grade-rag-systems-a-learning-series-f1878e012832) — Architecture patterns
- [RAG Architecture Components](https://galileo.ai/blog/rag-architecture) — Component responsibilities
- [Async RAG System with FastAPI](https://blog.futuresmart.ai/rag-system-with-async-fastapi-qdrant-langchain-and-openai) — Async patterns

### Tertiary Sources (LOW Confidence, Needs Validation)

**Performance claims requiring validation:**
- Semantic chunking 60% error reduction (single source) — validate during Phase 1 with manual inspection
- Knowledge graph 11% relevance improvement (single source) — validate during Phase 4 with eval harness
- Reranking 30-50% precision boost (multiple sources agree) — defer to post-POC validation

**Integration patterns:**
- LobeChat-custom backend integration (limited documentation) — test incrementally Days 2-5
- txtai graph vs Neo4j for POC scale (no direct comparison found) — start with txtai, switch if insufficient

---

**Research completed:** 2026-01-27
**Ready for roadmap:** YES
**Recommended next step:** Proceed to requirements definition with 6-phase structure
