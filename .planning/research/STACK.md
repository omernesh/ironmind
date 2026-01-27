# Technology Stack Research

**Domain:** RAG System with Knowledge Graph + Hybrid Retrieval
**Project:** DocRAG POC for IAI (Aerospace/Defense Technical Documentation)
**Researched:** 2026-01-27
**Overall Confidence:** HIGH

## Executive Summary

For a 5-day production-quality RAG POC handling aerospace/defense technical documentation, the recommended stack leverages **txtai 9.4.1** as the RAG orchestration backbone, **Docling 2.70.0** for document processing, **LobeChat** for the frontend interface, and **OpenAI GPT-4** for LLM capabilities. The knowledge graph layer uses **Neo4j 6.1** with Python driver integration, while hybrid retrieval combines txtai's native BM25 implementation with dense embeddings via **Sentence Transformers**. The system runs on **FastAPI** with **structured logging** (structlog/loguru), containerized via **Docker** with Python 3.11-slim base images.

This stack prioritizes:
- **Speed to production**: Pre-integrated components, minimal glue code
- **Enterprise requirements**: Auditability, traceability, explainability
- **Proven stability**: Battle-tested libraries with active 2025-2026 maintenance
- **5-day feasibility**: Avoids experimental tech, leverages turnkey solutions

## Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **txtai** | 9.4.1 | RAG orchestration, embeddings database, hybrid search | All-in-one framework combining vector search, BM25, LLM orchestration, and knowledge graph support. Production-ready with 50+ examples. Latest release Jan 23, 2026. | **HIGH** - [Official PyPI](https://pypi.org/project/txtai/), [GitHub releases](https://github.com/neuml/txtai/releases) |
| **Docling** | 2.70.0 | Document processing (PDF/DOCX parsing) | IBM-backed, LF AI & Data Foundation project. Advanced PDF understanding (tables, formulas, reading order). Native integrations with LangChain/LlamaIndex. Latest release Jan 23, 2026. | **HIGH** - [Official PyPI](https://pypi.org/project/docling/), [IBM announcement](https://www.ibm.com/new/announcements/granite-docling-end-to-end-document-conversion) |
| **LobeChat** | Latest | RAG frontend interface | Modern AI chat interface with native knowledge base/file upload, MCP support for RAG integration, multi-agent collaboration. Active development in 2025-2026. | **MEDIUM** - [GitHub](https://github.com/lobehub/lobe-chat), WebSearch (native RAG recently added) |
| **OpenAI GPT-4** | gpt-4o / gpt-4o-mini | LLM for generation | Industry-standard LLM with best-in-class performance. txtai integrates via LiteLLM for unified API. Gpt-4o-mini offers cost-effective alternative for POC. | **HIGH** - [OpenAI API](https://platform.openai.com/docs/models/), [txtai LLM docs](https://neuml.github.io/txtai/pipeline/text/llm/) |
| **Neo4j** | 6.1.0 | Knowledge graph database | Leading graph database with mature Python driver, GraphRAG package for LLM integration, monthly release cadence. LlamaIndex integration for property graphs. | **HIGH** - [Neo4j Python Driver 6.1](https://neo4j.com/docs/api/python-driver/current/), [PyPI neo4j](https://pypi.org/project/neo4j/) |
| **FastAPI** | Latest (0.1xx) | REST API framework | Modern, fast async Python framework. Native OpenAPI docs, perfect for RAG APIs. Strong observability ecosystem. Industry standard for AI APIs in 2026. | **HIGH** - WebSearch (production RAG standard), [FastAPI observability](https://grafana.com/grafana/dashboards/16110-fastapi-observability/) |
| **Python** | 3.11 | Runtime | Required by Docling 2.70+ (dropped 3.9 support), supported by txtai 9.4+. Python 3.11 offers 10-60% performance improvements over 3.10. Stable for production. | **HIGH** - [Docling requirements](https://pypi.org/project/docling/), Docker best practices |

## RAG-Specific Stack Components

### Embeddings & Retrieval

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Sentence Transformers** | Latest (3.x) | Dense embeddings generation | State-of-the-art text embeddings, 15,000+ pre-trained models on HuggingFace. Built into txtai. For technical docs, use models like `BAAI/bge-large-en-v1.5` with retrieval prefix. | **HIGH** - [HuggingFace org](https://huggingface.co/sentence-transformers), [docs](https://sbert.net/), WebSearch (2026 best practices) |
| **txtai Hybrid Search** | Built-in | BM25 + dense vector fusion | Native hybrid indexing in txtai 6.0+. Performant sparse index (Lucene-comparable). Reciprocal Rank Fusion for score combination. Enable with `hybrid=True`. | **HIGH** - [txtai 6.0 announcement](https://medium.com/neuml/whats-new-in-txtai-6-0-7d93eeedf804), [config docs](https://neuml.github.io/txtai/embeddings/configuration/general/) |
| **Reranker (Cross-Encoder)** | `ms-marco-MiniLM-L-12-v2` or txtai-compatible | Post-retrieval reranking | Reranking delivers 30-50% precision improvements in production RAG. Lightweight cross-encoder (33M params, 2-5ms CPU). Use for top-k candidates after hybrid retrieval. | **MEDIUM** - WebSearch ([Pinecone guide](https://www.pinecone.io/learn/series/rag/rerankers/), [2026 best practices](https://dev.to/suraj_khaitan_f893c243958/-rag-in-2026-a-practical-blueprint-for-retrieval-augmented-generation-16pp)) |

**Recommended Embedding Model for Technical Documentation:**
- **Primary**: `BAAI/bge-large-en-v1.5` (1024 dimensions, optimized for retrieval)
  - Use prompt prefix: `"Represent this sentence for searching relevant passages: "`
- **Alternative**: `intfloat/multilingual-e5-large` (if multilingual support needed)
  - Query prefix: `"query: "`, Passage prefix: `"passage: "`

### Knowledge Graph Integration

| Technology | Version | Purpose | When to Use | Confidence |
|------------|---------|---------|-------------|------------|
| **neo4j-graphrag** | Latest | GraphRAG pipeline for Neo4j | Use `SimpleKGPipeline` for automated knowledge graph construction from documents. Requires Neo4j connection + LLM + embeddings. | **MEDIUM** - [Neo4j Labs](https://neo4j.com/labs/genai-ecosystem/llamaindex/), [GitHub](https://github.com/neo4j/neo4j-graphrag-python) |
| **LlamaIndex PropertyGraphStore** | Latest | Graph construction & retrieval | Optional: For more sophisticated graph RAG patterns. Provides Neo4j integration with txtai/LlamaIndex workflows. 40-60% relevance improvement over vector-only. | **MEDIUM** - [LlamaIndex docs](https://developers.llamaindex.ai/python/examples/cookbooks/build_knowledge_graph_with_neo4j_llamacloud/), WebSearch (enterprise performance data) |

**Integration Pattern:**
1. **Parallel indexing**: Build txtai embeddings database + Neo4j knowledge graph simultaneously during document ingestion
2. **Hybrid retrieval at query time**: Vector/BM25 retrieval (txtai) + graph traversal (Neo4j Cypher queries)
3. **Context fusion**: Combine retrieved chunks with graph relationships for LLM context

### Observability & Logging

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **structlog** | Latest (24.x) | Structured JSON logging | Production-standard since 2013. JSON output for log aggregation. Rich context binding. Better than stdlib logging for RAG observability. | **HIGH** - [SigNoz guide](https://signoz.io/guides/structlog/), [Comprehensive guide](https://betterstack.com/community/guides/logging/structlog/) |
| **loguru** | Latest | Alternative: Simplified logging | Easier API than structlog, auto-serialization to JSON. Trade-off: No first-party OpenTelemetry integration (critical if adding traces later). | **MEDIUM** - [Better Stack comparison](https://betterstack.com/community/guides/logging/best-python-logging-libraries/), WebSearch (2026 best practices) |
| **Pydantic Logfire** (optional) | Latest | AI-specific observability | Purpose-built for LLM/RAG observability. Tracks LLM calls, vector searches, agent reasoning. Auto-instruments FastAPI, OpenAI. Consider for post-POC. | **MEDIUM** - [Pydantic Logfire](https://pydantic.dev/logfire), [FastAPI instrumentation](https://dev.to/devgeetech/observability-made-easy-adding-logs-traces-metrics-to-fastapi-with-logfire-529l) |

**Recommendation for 5-day POC**: Use **structlog** with JSON output. Defense industry values auditability—structured logs are table stakes. Defer full OpenTelemetry traces to post-POC.

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| **LiteLLM** | Latest | Multi-provider LLM proxy | Built into txtai for OpenAI/Claude/Bedrock support. Unified API for LLM switching. Use env var `OPENAI_API_KEY` for GPT-4. | **HIGH** - [txtai integration](https://neuml.github.io/txtai/pipeline/text/llm/), [LiteLLM docs](https://docs.litellm.ai/docs/providers/openai) |
| **pydantic** | 2.x | Data validation & settings | FastAPI dependency. Use for configuration validation, API request/response models. Version 2.x required for performance. | **HIGH** - Standard FastAPI dependency |
| **httpx** | Latest | Async HTTP client | For external API calls (OpenAI via LiteLLM, LobeChat integration). Async-first design matches FastAPI. | **HIGH** - txtai dependency (v9.4.1 fixed httpx import) |
| **pytest** + **pytest-asyncio** | Latest | Testing framework | Essential for RAG testing (retrieval quality, end-to-end). Async support for FastAPI routes. | **HIGH** - Python standard |

## Development & Deployment Stack

### Containerization

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Docker** | Latest (26.x) | Containerization | Industry standard. Multi-stage builds reduce image size 60-80%. Use for all services (API, Neo4j, LobeChat). | **HIGH** - [Docker 2026 best practices](https://medium.com/devops-ai-decoded/docker-in-2026-top-10-must-see-innovations-and-best-practices-for-production-success-30a5e090e5d6) |
| **Python 3.11-slim** | 3.11-slim-bookworm | Base image | **Strongly prefer over Alpine**. Alpine causes 50x slower builds (1500s vs 30s) due to musl libc + wheel recompilation. Slim images are secure, small (40-50MB base), fast. | **HIGH** - [PythonSpeed analysis](https://pythonspeed.com/articles/alpine-docker-python/), [Docker best practices](https://testdriven.io/blog/docker-best-practices/) |
| **docker-compose** | v2.x | Multi-container orchestration | Define txtai API + Neo4j + LobeChat as services. Volume management for knowledge graph persistence. | **HIGH** - Standard Docker tooling |

**Dockerfile Pattern (Multi-stage Build):**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Configuration Management

| Tool | Purpose | Pattern |
|------|---------|---------|
| **python-dotenv** | Environment variables | Load `.env` for local dev, use container env vars in production. Never commit API keys. |
| **Pydantic BaseSettings** | Typed configuration | Validate config at startup. Example: `OPENAI_API_KEY`, `NEO4J_URI`, `TXTAI_HYBRID=true`. |

## Installation & Setup

### Core Dependencies

```bash
# Core RAG stack
pip install txtai==9.4.1
pip install docling==2.70.0
pip install fastapi uvicorn[standard]
pip install neo4j==6.1.0

# Embeddings & retrieval
pip install sentence-transformers
pip install transformers  # Hugging Face models

# Logging & observability
pip install structlog

# Utilities
pip install pydantic[dotenv] httpx pytest pytest-asyncio

# Optional: Knowledge graph
pip install neo4j-graphrag  # For SimpleKGPipeline
```

### txtai with Hybrid Search

```bash
# Enable hybrid search in txtai
pip install txtai[api,graph,pipeline]  # Install with extras

# Configuration
embeddings_config = {
    "hybrid": True,  # Enable BM25 + dense vector hybrid search
    "content": True,  # Store content for retrieval
    "path": "embeddings-index",  # Persistence path
}
```

### Neo4j Setup

```bash
# Using Docker
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest
```

### Docling with OCR (Optional)

```bash
# Basic installation (no OCR)
pip install docling

# With OCR support (adds ~500MB dependencies)
pip install docling[easyocr]  # or [tesserocr] or [rapidocr]
```

**Recommendation for POC**: Skip OCR initially unless documents have scanned images. Adds complexity and processing time.

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative | Confidence |
|----------|-------------|-------------|-------------------------|------------|
| **RAG Framework** | txtai | LangChain | LangChain if you need extensive agent ecosystems or are already invested. txtai is faster to production for RAG-first use cases. | MEDIUM - Personal experience, [WebSearch comparison](https://www.firecrawl.dev/blog/best-open-source-rag-frameworks) |
| **RAG Framework** | txtai | LlamaIndex | LlamaIndex if you need sophisticated query engines or data connectors. More complex than txtai for basic RAG. | MEDIUM - [LlamaIndex docs](https://developers.llamaindex.ai/), ecosystem comparison |
| **Document Processing** | Docling | Unstructured.io | Unstructured.io if you need broader format support (emails, Slack, etc.). Docling excels specifically at PDF/DOCX technical documents. | MEDIUM - Domain-specific tradeoff |
| **Frontend** | LobeChat | Open WebUI / LibreChat | Open WebUI for broader LLM provider support. LibreChat for ChatGPT-like UI. LobeChat wins for native RAG/knowledge base features. | LOW - [Comparison article](https://blog.elest.io/the-best-open-source-chatgpt-interfaces-lobechat-vs-open-webui-vs-librechat/) |
| **Logging** | structlog | Python stdlib logging | Stdlib logging acceptable for simple POCs. Structlog essential for production observability with JSON output. | HIGH - [Best practices comparison](https://betterstack.com/community/guides/logging/best-python-logging-libraries/) |
| **Base Image** | python:3.11-slim | python:3.11-alpine | Alpine only if image size is critical AND you're willing to accept 50x slower builds + potential DNS/threading issues. Slim is better default. | HIGH - [Authoritative analysis](https://pythonspeed.com/articles/alpine-docker-python/) |
| **Graph Database** | Neo4j | PostgreSQL + pgvector | Postgres if you want single database for vectors + relations. Neo4j for true graph traversal, Cypher queries, GraphRAG patterns. | MEDIUM - Use case dependent |

## What NOT to Use

| Avoid | Why | Use Instead | Confidence |
|-------|-----|-------------|------------|
| **Python 3.9 or earlier** | Dropped by Docling 2.70.0 (Jan 2026). Incompatible with latest txtai optimizations. | Python 3.11+ (3.10 minimum) | **HIGH** |
| **Alpine base images (default)** | 50x slower builds, wheel recompilation, musl libc issues (DNS over TCP fails in K8s, stack size crashes). | python:3.11-slim-bookworm | **HIGH** |
| **Single-stage Dockerfiles** | 60-80% larger images, includes build tools in production. Security & size issues. | Multi-stage builds | **HIGH** |
| **Unverified embeddings models** | Stale embeddings hurt retrieval. Many models require specific prompt prefixes (e.g., "query:", "Represent this..."). | Tested models: bge-large-en-v1.5, e5-large with correct prefixes | **MEDIUM** |
| **Vector-only retrieval** | Misses exact keyword matches. BM25 + vector hybrid is production standard in 2026. | txtai hybrid search (BM25 + dense) | **HIGH** |
| **Global logging config** | Hard to test, non-deterministic in FastAPI async context. | Structured logging with context binding (structlog) | **MEDIUM** |
| **Old Neo4j driver package** | `neo4j-driver` deprecated since 6.0.0 (no updates). | `neo4j` package (version 6.1+) | **HIGH** |

## Stack Patterns by Use Case

### Pattern 1: Basic Hybrid RAG (Day 1-2)
**Goal**: Get retrieval working with BM25 + vectors
```python
# Minimal viable stack
- txtai with hybrid=True
- Docling for doc processing
- FastAPI for API
- structlog for logging
- Docker compose
```
**Skip**: Knowledge graph, reranking, LobeChat integration

### Pattern 2: Graph-Enhanced RAG (Day 3-4)
**Goal**: Add knowledge graph for relationship-aware retrieval
```python
# Add to Pattern 1
- Neo4j container
- neo4j-graphrag for KG construction
- Parallel retrieval: txtai + Neo4j Cypher
```
**Complexity**: Graph schema design, entity extraction quality

### Pattern 3: Production-Ready RAG (Day 5)
**Goal**: Polish for demo with frontend + observability
```python
# Add to Pattern 2
- LobeChat frontend
- Enhanced structlog (request IDs, timing)
- Docker health checks
- pytest integration tests
```

## Version Compatibility Matrix

| Component | Version | Compatible With | Notes |
|-----------|---------|-----------------|-------|
| Python | 3.11 | All listed packages | Docling requires 3.10+, txtai 3.10+ |
| txtai | 9.4.1 | Python 3.10+, sentence-transformers 3.x | Latest release Jan 23, 2026 |
| Docling | 2.70.0 | Python 3.10-3.12 | Dropped Python 3.9 in this version |
| Neo4j | 6.1.0 driver | Neo4j 5.x+ server | Monthly release cadence |
| FastAPI | 0.1xx | Python 3.8+ (but use 3.11) | Stable, mature API |
| LiteLLM | Latest | OpenAI API, txtai 9.4+ | Built into txtai LLM pipeline |

**Critical Compatibility Notes:**
- txtai 9.4.1 fixed httpx import issue (use this exact version or newer)
- Neo4j driver 6.x uses different package name (`neo4j` not `neo4j-driver`)
- Sentence Transformers 3.x has breaking changes from 2.x (check model loading)

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         LobeChat                            │
│                      (Frontend UI)                          │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP API
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Docling       │  │   txtai     │  │  Neo4j Client   │  │
│  │  (Doc Parser)  │─▶│  (Hybrid    │◀─│  (KG Queries)   │  │
│  └────────────────┘  │   Search)   │  └─────────────────┘  │
│                      │             │                        │
│                      │  • BM25     │                        │
│                      │  • Vectors  │                        │
│                      │  • Rerank   │                        │
│                      └──────┬──────┘                        │
│                             │                               │
│                             ▼                               │
│                      ┌─────────────┐                        │
│                      │  LiteLLM    │                        │
│                      │  (GPT-4)    │                        │
│                      └─────────────┘                        │
│                                                             │
│  Observability: structlog (JSON) ────────────────▶ Logs    │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │       Neo4j Database          │
        │    (Knowledge Graph Store)    │
        └───────────────────────────────┘
```

## Timeline-Aware Stack Decisions

### Days 1-2: Foundation
**Focus**: Get basic retrieval working
- txtai embeddings + hybrid search
- Docling document ingestion
- FastAPI basic endpoints
- Local testing (no Docker yet)

**Defer**: Knowledge graph, frontend, advanced logging

### Days 3-4: Enhancement
**Focus**: Add knowledge graph + reranking
- Neo4j integration via docker-compose
- Knowledge graph construction pipeline
- Reranker post-processing
- Structured logging (structlog)

**Defer**: Frontend polish, comprehensive tests

### Day 5: Integration & Polish
**Focus**: End-to-end demo readiness
- LobeChat frontend integration
- Docker compose orchestration
- Basic integration tests
- Documentation + demo script

## Research Quality Assessment

### High Confidence Components (PRIMARY: Context7, Official Docs, Recent Releases)
- txtai version & capabilities (PyPI + GitHub releases, Jan 2026)
- Docling version & requirements (PyPI, Jan 2026)
- Neo4j driver 6.1 (official docs)
- Python Docker best practices (authoritative sources)
- Hybrid search necessity (multiple 2026 sources)

### Medium Confidence Components (SECONDARY: Multiple credible sources)
- LobeChat RAG integration (GitHub discussions + recent issues)
- Reranking models & performance (multiple 2026 guides)
- Knowledge graph performance claims (single credible source)
- LlamaIndex + Neo4j patterns (official labs documentation)

### Low Confidence / Needs Validation
- Specific LobeChat-txtai integration pattern (limited documentation)
- Exact performance numbers for hybrid vs vector-only (varies by use case)
- Reranker model selection for technical docs (domain-specific testing needed)

## Sources

### Primary Sources (HIGH Confidence)
- [txtai PyPI (9.4.1)](https://pypi.org/project/txtai/) - Official package, version verification
- [txtai GitHub Releases](https://github.com/neuml/txtai/releases) - Release notes, Jan 2026
- [Docling PyPI (2.70.0)](https://pypi.org/project/docling/) - Official package, Python version requirements
- [Neo4j Python Driver 6.1](https://neo4j.com/docs/api/python-driver/current/) - Official documentation
- [txtai Hybrid Search (Medium article)](https://medium.com/neuml/whats-new-in-txtai-6-0-7d93eeedf804) - Direct from maintainer
- [Python Docker Alpine Issues](https://pythonspeed.com/articles/alpine-docker-python/) - Authoritative performance analysis

### Secondary Sources (MEDIUM Confidence)
- [15 Best RAG Frameworks 2026](https://www.firecrawl.dev/blog/best-open-source-rag-frameworks)
- [Hybrid RAG Production Standard](https://dev.to/suraj_khaitan_f893c243958/-rag-in-2026-a-practical-blueprint-for-retrieval-augmented-generation-16pp)
- [Reranking Best Practices](https://www.pinecone.io/learn/series/rag/rerankers/)
- [FastAPI Observability Stack](https://github.com/blueswen/fastapi-observability)
- [Structured Logging Comparison](https://betterstack.com/community/guides/logging/best-python-logging-libraries/)
- [LobeChat GitHub Discussions](https://github.com/lobehub/lobe-chat/discussions/1507)
- [Neo4j GraphRAG for Python](https://neo4j.com/blog/developer/knowledge-graphs-neo4j-graphrag-for-python/)
- [Docker 2026 Best Practices](https://medium.com/devops-ai-decoded/docker-in-2026-top-10-must-see-innovations-and-best-practices-for-production-success-30a5e090e5d6)

### Ecosystem Discovery (WebSearch Verified)
- IBM Granite-Docling announcement (Jan 2026)
- LlamaIndex + Neo4j integration patterns
- Sentence Transformers 2026 best practices
- Hybrid retrieval performance claims (30-50% improvements)

---

**Stack Research Complete**
- **Timeline feasibility**: HIGH - All components production-ready, well-documented
- **Integration complexity**: MEDIUM - txtai + Neo4j parallel indexing needs testing
- **Risk areas**: LobeChat integration (less documented), knowledge graph schema design
- **Recommended path**: Build incrementally (Pattern 1 → 2 → 3) to validate at each stage

*Research completed: 2026-01-27 | Next: FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
