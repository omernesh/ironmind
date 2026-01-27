# Architecture Research: RAG System with Knowledge Graph + Hybrid Retrieval

**Domain:** Document-based RAG systems with knowledge graph integration and hybrid retrieval
**Researched:** 2026-01-27
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend Layer (LobeChat)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Chat UI  │  │ Upload   │  │ Auth     │  │ History  │         │
│  │          │  │ Manager  │  │ (Better) │  │ Display  │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
├───────┴──────────────┴──────────────┴──────────────┴─────────────┤
│                     API Gateway (FastAPI)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐     │
│  │ Ingestion API   │  │ Chat/Query API  │  │ Admin API    │     │
│  │ /ingest         │  │ /chat, /query   │  │ /health      │     │
│  └────┬────────────┘  └────┬────────────┘  └──────────────┘     │
├───────┴──────────────────────┴───────────────────────────────────┤
│                   RAG Orchestration Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │ Document     │  │ Hybrid       │  │ Response         │       │
│  │ Processor    │  │ Retriever    │  │ Generator        │       │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘       │
├─────────┴──────────────────┴──────────────────┴───────────────────┤
│                   Processing Services Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │ Docling      │  │ txtai        │  │ OpenAI LLM       │       │
│  │ Parser       │  │ Embeddings   │  │ GPT-4            │       │
│  │              │  │ + Graph      │  │                  │       │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘       │
├─────────┴──────────────────┴──────────────────┴───────────────────┤
│                      Storage Layer                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │ Vector     │  │ Graph      │  │ BM25       │  │ Metadata   │ │
│  │ Index      │  │ Network    │  │ Index      │  │ Store      │ │
│  │ (txtai)    │  │ (txtai)    │  │ (txtai)    │  │ (txtai)    │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **LobeChat Frontend** | User interface, auth UI, document upload, chat interaction | Next.js app with Better Auth, pre-built chat components |
| **FastAPI Backend** | API routing, request validation, authentication enforcement, orchestration | Python FastAPI with async/await, Pydantic models |
| **Document Processor** | Parse documents (DOCX/PDF), extract structure, chunk with metadata | Docling for parsing, custom chunking logic |
| **Hybrid Retriever** | Dual-channel retrieval (semantic + keyword), rank fusion | txtai embeddings + BM25, RRF algorithm |
| **txtai Embeddings** | Vector search, sparse search, graph storage, unified index | all-in-one embeddings database (ann + database + vectors) |
| **Knowledge Graph** | Entity/relation extraction, graph storage, graph-aware retrieval | txtai graph component, entity extraction pipeline |
| **Response Generator** | Context-aware prompt building, LLM invocation, streaming responses | OpenAI GPT-4 API with async streaming |
| **Observability** | Structured logging, request tracking, performance metrics | Python logging with JSON formatter, correlation IDs |

## Recommended Project Structure

```
docrag-poc/
├── frontend/                    # LobeChat deployment
│   ├── Dockerfile              # LobeChat container build
│   ├── .env.example            # Frontend environment variables
│   └── config/                 # LobeChat configuration
│       └── lobechat.config.js  # API endpoint, auth settings
├── backend/                     # FastAPI RAG backend
│   ├── app/
│   │   ├── api/                # API routes
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py   # POST /ingest endpoint
│   │   │   ├── chat.py         # POST /chat, /query endpoints
│   │   │   └── health.py       # GET /health, /metrics
│   │   ├── services/           # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py  # Docling integration
│   │   │   ├── indexer.py             # txtai indexing
│   │   │   ├── retriever.py           # Hybrid retrieval
│   │   │   ├── graph_builder.py       # KG construction
│   │   │   └── generator.py           # LLM generation
│   │   ├── models/             # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── requests.py     # Request models
│   │   │   └── responses.py    # Response models
│   │   ├── core/               # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── config.py       # Settings (12-factor)
│   │   │   ├── logging.py      # Structured logging
│   │   │   └── auth.py         # Auth middleware
│   │   └── main.py             # FastAPI app initialization
│   ├── tests/                  # Unit + integration tests
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Backend container
│   └── .env.example            # Backend environment variables
├── infra/                       # Infrastructure as code
│   ├── docker-compose.yml      # Multi-container orchestration
│   ├── docker-compose.prod.yml # Production overrides
│   └── nginx.conf              # Reverse proxy config (optional)
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md         # System architecture
│   ├── DEPLOYMENT.md           # Deployment guide
│   ├── PIPELINE_DESIGN.md      # RAG pipeline details
│   └── EXAMPLE_QUERIES.md      # Demo Q&A examples
├── .gitignore
├── README.md                    # Project overview
├── CONTRIBUTING.md              # Development guidelines
└── LICENSE                      # MIT license
```

### Structure Rationale

- **frontend/ and backend/ separation:** Clear boundary between LobeChat deployment and custom FastAPI backend. Each has independent Dockerfile and dependencies.
- **backend/app/services/:** Business logic separated from API routes. Enables testing services independently, swap implementations (e.g., switch from Docling to alternative parser).
- **backend/app/models/:** Pydantic models for request/response validation. FastAPI auto-generates OpenAPI docs from these schemas.
- **infra/:** Infrastructure configuration co-located with code. Docker Compose for local dev and VPS deployment (POC scale doesn't require Kubernetes).
- **docs/:** Assignment deliverable documentation at top level for easy reviewer access.

## Architectural Patterns

### Pattern 1: Dual-Channel Hybrid Retrieval with Rank Fusion

**What:** Parallel execution of semantic (vector) and lexical (BM25) retrieval, followed by result fusion using Reciprocal Rank Fusion (RRF).

**When to use:** Technical documents with precise terminology (IDs, configuration keys, API names) that require exact matches alongside semantic understanding.

**Trade-offs:**
- **Pros:** 15-30% better recall than either method alone; handles both semantic questions ("how does authentication work?") and keyword questions ("what is the FC-2050 configuration?")
- **Cons:** Higher latency (100-300ms) vs BM25 alone; requires maintaining two indexes

**Example:**
```python
# backend/app/services/retriever.py
from txtai.embeddings import Embeddings

class HybridRetriever:
    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings

    async def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        # Parallel retrieval from both indexes
        vector_results = await self.embeddings.search(
            query,
            limit=top_k * 2  # Over-retrieve for fusion
        )

        bm25_results = await self.embeddings.bm25(
            query,
            limit=top_k * 2
        )

        # Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            vector_results,
            bm25_results,
            k=60  # RRF constant
        )

        return fused_results[:top_k]

    def _reciprocal_rank_fusion(self, list1, list2, k=60):
        """Merge two ranked lists using RRF algorithm"""
        scores = {}
        for rank, doc in enumerate(list1):
            scores[doc['id']] = scores.get(doc['id'], 0) + 1 / (k + rank + 1)
        for rank, doc in enumerate(list2):
            scores[doc['id']] = scores.get(doc['id'], 0) + 1 / (k + rank + 1)

        # Sort by fused score descending
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Pattern 2: Structured Document Ingestion with Metadata Preservation

**What:** Multi-stage pipeline that parses documents, preserves structural metadata (headings, sections, page numbers), chunks intelligently, and indexes with metadata.

**When to use:** Technical documents where source traceability is critical for explainability and auditability (aerospace/defense context).

**Trade-offs:**
- **Pros:** Preserves document structure, enables precise citations, improves retrieval accuracy
- **Cons:** More complex than naive chunking, requires format-specific parsing

**Example:**
```python
# backend/app/services/document_processor.py
from docling.document_converter import DocumentConverter
from docling.datamodel.document import DoclingDocument

class DocumentProcessor:
    def __init__(self):
        self.converter = DocumentConverter()

    async def process(self, file_path: str, user_id: str) -> list[dict]:
        # Parse with Docling (preserves structure)
        doc: DoclingDocument = await self.converter.convert(file_path)

        chunks = []
        for section in doc.sections:
            # Recursive chunking within sections
            section_chunks = self._chunk_section(
                section.text,
                max_chunk_size=512,
                overlap=50
            )

            for idx, chunk_text in enumerate(section_chunks):
                chunks.append({
                    "id": f"{doc.id}_{section.id}_{idx}",
                    "text": chunk_text,
                    "metadata": {
                        "user_id": user_id,
                        "doc_id": doc.id,
                        "filename": doc.filename,
                        "section_heading": section.heading,
                        "page_range": section.page_range,
                        "chunk_index": idx
                    }
                })

        return chunks

    def _chunk_section(self, text: str, max_chunk_size: int, overlap: int):
        """Recursive chunking preserving sentence boundaries"""
        # Implementation: split on sentences, group to max_chunk_size
        pass
```

### Pattern 3: Async Streaming Response with Citation Injection

**What:** Asynchronous FastAPI endpoint that streams LLM tokens to frontend while injecting inline citations from retrieval metadata.

**When to use:** User-facing chat interfaces where perceived latency matters (5-8 second target response time).

**Trade-offs:**
- **Pros:** Reduces Time-to-First-Token (TTFT), better UX for long answers
- **Cons:** More complex error handling, requires async throughout stack

**Example:**
```python
# backend/app/api/chat.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
import json

app = FastAPI()
client = AsyncOpenAI()

@app.post("/chat")
async def chat_stream(request: ChatRequest):
    # Retrieve context
    retriever = get_retriever()
    context_chunks = await retriever.retrieve(request.query, top_k=5)

    # Build prompt with context
    prompt = build_prompt(request.query, context_chunks)

    async def generate():
        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'token': token})}\n\n"

        # Append citations after answer
        citations = format_citations(context_chunks)
        yield f"data: {json.dumps({'citations': citations})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Pattern 4: Knowledge Graph Integration for Multi-Hop Retrieval

**What:** Entity and relation extraction during ingestion, graph storage alongside vectors, graph-aware retrieval for multi-hop questions.

**When to use:** Technical documents with rich entity relationships (service → depends on → component → configured by → parameter).

**Trade-offs:**
- **Pros:** Enables complex multi-hop questions, improves context relevance by 11% over vector-only RAG
- **Cons:** Higher ingestion cost (entity extraction), requires domain-specific entity types

**Example:**
```python
# backend/app/services/graph_builder.py
from txtai.pipeline import Labels

class GraphBuilder:
    def __init__(self):
        # Use txtai's label extraction pipeline
        self.entity_extractor = Labels()

    async def build_graph(self, chunks: list[dict]) -> dict:
        """Extract entities and relations, build graph"""
        entities = []
        relations = []

        for chunk in chunks:
            # Extract entities (services, components, configs)
            extracted = self.entity_extractor(
                chunk["text"],
                labels=["SERVICE", "COMPONENT", "CONFIGURATION", "PARAMETER"]
            )

            for entity in extracted:
                entities.append({
                    "id": entity["id"],
                    "type": entity["label"],
                    "text": entity["text"],
                    "chunk_id": chunk["id"]
                })

            # Extract relations (simple pattern-based for POC)
            relations.extend(self._extract_relations(chunk["text"], entities))

        return {
            "entities": entities,
            "relations": relations
        }

    def _extract_relations(self, text: str, entities: list[dict]) -> list[dict]:
        """Pattern-based relation extraction"""
        # Example: "Service A depends on Component B"
        # For POC: simple regex patterns
        # For production: use dependency parsing or LLM-based extraction
        pass
```

## Data Flow

### Ingestion Flow

```
User uploads document (DOCX/PDF)
    ↓
[LobeChat Upload UI] → POST /ingest with file
    ↓
[FastAPI Ingestion API] → validates auth, file type
    ↓
[Document Processor] → Docling parses to structured format
    ↓ (DoclingDocument)
[Chunker] → recursive chunking with metadata preservation
    ↓ (chunks with metadata)
[Graph Builder] → entity/relation extraction (optional)
    ↓ (entities, relations)
[txtai Indexer] → creates embeddings, BM25 index, stores graph
    ↓ (indexed)
[Vector Store + BM25 + Graph] ← persisted to disk
    ↓
[Response] ← 200 OK with document_id
```

### Query Flow (Retrieval + Generation)

```
User asks question in chat
    ↓
[LobeChat] → POST /chat with query + conversation_history
    ↓
[FastAPI Chat API] → validates auth, rate limits
    ↓
[Hybrid Retriever]
    ├─→ [Vector Search] → semantic similarity (top 10)
    └─→ [BM25 Search] → keyword matching (top 10)
    ↓ (parallel)
[Rank Fusion] → RRF merges results → top 5 chunks
    ↓ (optional graph enhancement)
[Graph Retriever] → expands context with related entities
    ↓ (retrieved chunks + metadata)
[Prompt Builder] → formats context + query into prompt
    ↓ (prompt)
[LLM Generator] → OpenAI GPT-4 streaming
    ↓ (token stream)
[Citation Injector] → adds source metadata inline
    ↓
[Response Stream] → SSE to frontend
    ↓
[LobeChat] → displays answer with citations
```

### Key Data Flows

1. **Document-to-Index:** Docling → chunks → embeddings/BM25/graph → txtai unified index
2. **Query-to-Answer:** Query → hybrid retrieval → context + prompt → LLM → streamed response
3. **Auth Flow:** LobeChat Better Auth → JWT token → FastAPI middleware → user_id extraction
4. **Observability:** Every request → correlation_id → structured logs → stdout (Docker captures)

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **POC (2-3 users, 10 docs)** | Monolithic FastAPI + txtai in-memory index, SQLite for metadata, single Docker container. No separate vector DB needed. |
| **Small Production (10-50 users, 100-500 docs)** | Persist txtai index to disk, add Redis for caching frequently retrieved chunks, move to Postgres for metadata. Still single-node deployment. |
| **Medium Scale (100-1000 users, 1000+ docs)** | Split into microservices: separate ingestion service, query service, LLM gateway. Introduce dedicated vector DB (Qdrant, Weaviate). Add load balancer. |
| **Large Scale (1000+ users)** | Horizontal scaling with Kubernetes, distributed vector DB (Milvus cluster), async job queue (Celery) for ingestion, CDN for document storage. |

### Scaling Priorities for POC → Production

1. **First bottleneck: LLM latency (5-8 sec response time)**
   - **Fix:** Add semantic caching layer (cache embeddings of common questions)
   - **Fix:** Use faster embedding model (all-MiniLM-L6-v2 is fast, consider distilbert for even faster)
   - **Fix:** Reduce context size from retrieved chunks (summarize before sending to LLM)

2. **Second bottleneck: Concurrent ingestion (multiple users uploading simultaneously)**
   - **Fix:** Move ingestion to async task queue (Celery + Redis)
   - **Fix:** Add job status endpoint for "Processing... 45% complete"

3. **Third bottleneck: Vector search latency at scale**
   - **Fix:** Move from txtai in-memory to persistent vector DB with HNSW index
   - **Fix:** Shard index by user or document collection

## Anti-Patterns

### Anti-Pattern 1: Naive Chunking Without Metadata

**What people do:** Split documents by fixed character count (e.g., every 500 characters) without preserving section headings, page numbers, or document structure.

**Why it's wrong:** Loses source traceability. When LLM cites a chunk, user can't find original source. Breaks sentences mid-thought. Especially problematic for aerospace/defense docs where precision is critical.

**Do this instead:** Use format-aware parsing (Docling), chunk at section boundaries or semantic boundaries (paragraph, heading), preserve metadata (section title, page range, document ID) with every chunk. Store metadata alongside embeddings for citation.

### Anti-Pattern 2: LLM-Based Entity Extraction for Every Document

**What people do:** Use GPT-4 to extract entities and relations from every chunk during ingestion.

**Why it's wrong:** Extremely expensive ($$$), slow (adds 30-60 seconds per document), doesn't scale beyond POC. Recent research shows dependency-based NLP extraction achieves 94% of LLM performance at fraction of cost.

**Do this instead:** For POC, use rule-based or pattern-based extraction (regex for IDs, NER for technical terms). For production, use lightweight NLP libraries (spaCy with custom entity ruler). Reserve LLM for complex relation extraction only when needed.

### Anti-Pattern 3: Synchronous API for Long-Running Operations

**What people do:** Block API response until ingestion completes (file upload → parse → chunk → index → return).

**Why it's wrong:** Large documents take 30-90 seconds to process. Frontend times out, user doesn't know if upload succeeded, can't handle concurrent uploads.

**Do this instead:** Return 202 Accepted immediately with job_id. Process in background async task. Provide /status/{job_id} endpoint for polling. Use WebSocket or SSE for real-time progress updates.

### Anti-Pattern 4: Global txtai Index Without User Isolation

**What people do:** Store all users' documents in single shared txtai index.

**Why it's wrong:** User A can retrieve User B's documents via semantic search. Critical security vulnerability for sensitive aerospace/defense docs.

**Do this instead:** Either (a) create separate txtai index per user (simple for POC, doesn't scale), or (b) use single index with metadata filtering (`embeddings.search(query, where={"user_id": user_id})`). Option (b) recommended for production.

### Anti-Pattern 5: No Reranking After Hybrid Retrieval

**What people do:** Return top-k results from RRF directly to LLM without further refinement.

**Why it's wrong:** RRF is a simple heuristic. Top results may include redundant chunks or false positives. Wastes context window on low-quality chunks.

**Do this instead:** Add reranking stage after RRF using cross-encoder model (e.g., ms-marco-MiniLM) or diversity-based filtering (MMR - Maximal Marginal Relevance). For POC, reranking may be overkill, but consider for production.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **OpenAI GPT-4** | Async REST API, streaming responses | Use official `openai` Python client with `AsyncOpenAI`. Handle rate limits (429) with exponential backoff. Stream tokens via SSE. |
| **LobeChat → Backend** | REST API over HTTP | LobeChat makes POST to `/chat`, `/ingest` endpoints. Use CORS middleware in FastAPI. Pass JWT token in `Authorization: Bearer` header. |
| **Docling** | In-process Python library | Import directly in FastAPI service. No separate service. Handles DOCX/PDF/PPTX. Configure timeout (90-120 sec for large docs). |
| **txtai** | In-process Python library | Embeddings database runs in same process as FastAPI. No separate server. Index persists to disk at shutdown. Load at startup. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **API ↔ Services** | Direct function calls | API routes import service classes. Keep API layer thin (validation only). All business logic in services layer. |
| **Services ↔ txtai** | Method calls on `Embeddings` object | Single `Embeddings` instance shared across requests. Thread-safe. Use async wrappers for I/O operations. |
| **Frontend ↔ Backend** | HTTP/REST + SSE | Standard REST for CRUD. SSE (Server-Sent Events) for streaming chat responses. Consider WebSocket if bidirectional needed. |
| **Ingestion ↔ Indexing** | Async task queue (future) | For POC: synchronous in-process. For production: Celery task queue with Redis broker. Decouple upload from indexing. |

### Docker Compose Service Architecture

```yaml
# infra/docker-compose.yml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TXTAI_INDEX_PATH=/data/txtai_index
    volumes:
      - txtai_data:/data
      - uploaded_docs:/app/uploads

volumes:
  txtai_data:
  uploaded_docs:
```

**Key decisions:**
- **Single-node deployment:** All services on one VPS for POC scale
- **Volume mounts:** Persist txtai index and uploaded documents across container restarts
- **Environment variables:** 12-factor config, sensitive keys from `.env` file
- **Health checks:** Add `healthcheck` to ensure backend is ready before frontend starts

## Deployment Architecture (Docker Compose on VPS)

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS (Hetzner CX21/CX31)                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 Docker Engine                           │ │
│  │                                                         │ │
│  │  ┌──────────────────┐      ┌──────────────────┐       │ │
│  │  │  frontend        │      │  backend         │       │ │
│  │  │  (LobeChat)      │◄────►│  (FastAPI)       │       │ │
│  │  │  Port: 3000      │      │  Port: 8000      │       │ │
│  │  └──────────────────┘      └─────────┬────────┘       │ │
│  │                                       │                 │ │
│  │                              ┌────────▼────────┐        │ │
│  │                              │  txtai index    │        │ │
│  │                              │  (volume mount) │        │ │
│  │                              └─────────────────┘        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Nginx (optional reverse proxy)                        │ │
│  │  HTTPS termination, /api → backend, / → frontend       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         ▲                                       ▲
         │ HTTPS (443)                           │ API calls
         │                                       │
    [Internet]                         [OpenAI API]
```

## Sources

### Hybrid Retrieval Architecture
- [Hybrid RAG in the Real World: Graphs, BM25, and the End of Black-Box Retrieval - NetApp](https://community.netapp.com/t5/Tech-ONTAP-Blogs/Hybrid-RAG-in-the-Real-World-Graphs-BM25-and-the-End-of-Black-Box-Retrieval/ba-p/464834)
- [Advanced RAG: From Naive Retrieval to Hybrid Search and Re-ranking](https://dev.to/kuldeep_paul/advanced-rag-from-naive-retrieval-to-hybrid-search-and-re-ranking-4km3)
- [Hybrid Retrieval for Enterprise RAG: When to Use BM25, Vectors, or Both](https://ragaboutit.com/hybrid-retrieval-for-enterprise-rag-when-to-use-bm25-vectors-or-both/)

### Knowledge Graph Integration
- [Towards Practical GraphRAG: Efficient Knowledge Graph Construction and Hybrid Retrieval at Scale](https://arxiv.org/html/2507.03226v3)
- [GraphRAG Explained: Enhancing RAG with Knowledge Graphs - Zilliz](https://medium.com/@zilliz_learn/graphrag-explained-enhancing-rag-with-knowledge-graphs-3312065f99e1)
- [HybridRAG: Integrating Knowledge Graphs and Vector Retrieval](https://arxiv.org/html/2408.04948v1)

### Production RAG Architecture
- [RAG at Scale: How to Build Production AI Systems in 2026 - Redis](https://redis.io/blog/rag-at-scale/)
- [Building Production-Grade RAG Systems - Medium](https://medium.com/@kranthigoud975/building-production-grade-rag-systems-a-learning-series-f1878e012832)
- [RAG Architecture Components - Galileo](https://galileo.ai/blog/rag-architecture)

### txtai Architecture
- [txtai Embeddings Documentation](https://neuml.github.io/txtai/embeddings/)
- [txtai GitHub Repository](https://github.com/neuml/txtai)
- [Introducing txtai, the all-in-one AI framework - NeuML Medium](https://medium.com/neuml/introducing-txtai-the-all-in-one-ai-framework-0660ecfc39d7)

### Document Processing
- [Docling Documentation - Pipeline Options](https://docling-project.github.io/docling/reference/pipeline_options/)
- [Docling Standard PDF Pipeline](https://deepwiki.com/docling-project/docling/5.1-standard-pdf-pipeline)
- [RAG Document Chunking: 6 Best Practices - Airbyte](https://airbyte.com/agentic-data/ag-document-chunking-best-practices)
- [Building Production-Ready Azure Document Ingestion Pipeline - Medium](https://medium.com/@shaafabdullah/building-a-production-ready-azure-document-ingestion-pipeline-8272a71fe142)

### FastAPI Async Patterns
- [Async RAG System with FastAPI, Qdrant & LangChain](https://blog.futuresmart.ai/rag-system-with-async-fastapi-qdrant-langchain-and-openai)
- [Building a RAG System with LangChain and FastAPI - DataCamp](https://www.datacamp.com/tutorial/building-a-rag-system-with-langchain-and-fastapi)
- [Building RAGenius: Production-Ready RAG with FastAPI](https://dev.to/aquibpy/building-ragenius-a-production-ready-rag-system-with-fastapi-azure-openai-chromadb-3281)

### LobeChat Architecture
- [LobeChat Architecture - GitHub Wiki](https://github.com/lobehub/lobe-chat/wiki/Architecture)
- [LobeChat GitHub Repository](https://github.com/lobehub/lobe-chat)

### Docker Compose Deployment
- [NVIDIA RAG Blueprint - GitHub](https://github.com/NVIDIA-AI-Blueprints/rag)
- [Retrieval-Augmented Generation using Docker Compose - Medium](https://medium.com/@sreetej24/retrieval-augmented-generation-rag-application-using-docker-compose-part-1-4c86adfe41a3)

---
*Architecture research for: DocRAG POC with Knowledge Graph + Hybrid Retrieval*
*Researched: 2026-01-27*
*Confidence: HIGH - Research based on recent 2025-2026 sources, production implementations, and official documentation*
