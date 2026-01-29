# IRONMIND Architecture

## Overview

IRONMIND is a RAG (Retrieval-Augmented Generation) system for technical document analysis. This document describes the system architecture, components, and data flow.

## System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Interface                             │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────────────┐    │
│  │  Landing   │  │   Dashboard    │  │    Chat Interface      │    │
│  │   Page     │  │ (Upload/List)  │  │  (Q&A with Citations)  │    │
│  └────────────┘  └────────────────┘  └────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
                                │
                          Better Auth
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend API (FastAPI)                        │
│  ┌──────────┐  ┌────────────────┐  ┌───────────────────────────┐  │
│  │ Document │  │  Chat          │  │  Debug Endpoints          │  │
│  │ Router   │  │  Router        │  │  (Graph inspection)       │  │
│  └────┬─────┘  └───────┬────────┘  └───────────────────────────┘  │
│       │                │                                            │
│  ┌────▼────────────────▼────────────────────────────────────────┐  │
│  │                    Service Layer                              │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐   │  │
│  │  │Pipeline │  │Retriever │  │Reranker │  │  Generator   │   │  │
│  │  └────┬────┘  └────┬─────┘  └────┬────┘  └──────┬───────┘   │  │
│  └───────┼────────────┼─────────────┼───────────────┼───────────┘  │
└──────────┼────────────┼─────────────┼───────────────┼──────────────┘
           │            │             │               │
           ▼            ▼             ▼               ▼
┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐
│   Docling    │  │  txtai   │  │DeepInfra │  │  OpenAI    │
│   (Parsing)  │  │ (Index)  │  │(Rerank)  │  │ (LLM+Embed)│
└──────────────┘  └──────────┘  └──────────┘  └────────────┘
                       │
                       ▼
                ┌──────────────┐
                │  FalkorDB    │
                │   (Graph)    │
                └──────────────┘
```

## Data Flow

### Document Ingestion

1. **Upload**: User uploads PDF/DOCX via frontend
2. **Parse**: Docling extracts structured content (sections, headings, pages)
3. **Chunk**: Semantic chunking preserves context boundaries (~1000 tokens)
4. **Extract**: LLM extracts entities and relationships for knowledge graph
5. **Index**: Chunks indexed in txtai with OpenAI embeddings
6. **Store**: Graph stored in FalkorDB, metadata in SQLite

### Query Processing

1. **Retrieve**: Hybrid search (semantic + BM25) returns top-25 chunks
2. **Expand**: Document relationships add related document chunks
3. **Rerank**: Cross-encoder reranks to top-12
4. **Generate**: GPT-5-mini generates answer with citations from top-10

## Component Details

### Frontend (Next.js 16)

- **Better Auth**: Session management with SQLite backend
- **App Router**: Server components for SEO, client components for interactivity
- **API Client**: Token exchange for backend authentication

### Backend (FastAPI)

- **Routers**: documents, chat, health, debug
- **Services**: Pipeline, Retriever, Reranker, Generator
- **Middleware**: CORS, Request ID correlation, JWT validation

### External Services

| Service | Purpose | Model |
|---------|---------|-------|
| Docling | Document parsing | docling-serve v1.10.0 |
| OpenAI | Embeddings | text-embedding-3-small |
| OpenAI | Generation | gpt-5-mini |
| DeepInfra | Reranking | Qwen3-Reranker-0.6B |
| FalkorDB | Graph storage | Latest |

## Security

- JWT tokens for API authentication (15-min expiry)
- Non-root Docker users
- CORS origin validation
- Input validation on all endpoints
- No secrets in client bundles

## Scalability Considerations

Current POC design (2-3 users, 10 docs each):

- Single backend instance with Gunicorn (4 workers)
- SQLite for auth and document metadata
- txtai with file-based index

For scaling beyond POC:
- Postgres for metadata
- Redis for caching
- Distributed task queue for processing
- Horizontal backend scaling
