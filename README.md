# IRONMIND

Technical Document Intelligence for Aerospace & Defense

IRONMIND is a RAG (Retrieval-Augmented Generation) system designed for technical documentation analysis. It enables users to upload technical documents and receive AI-powered answers with transparent source citations.

## Features

- **Document Upload**: Support for PDF and DOCX documents (up to 10 per user)
- **Hybrid Retrieval**: Semantic search + BM25 keyword matching with RRF fusion
- **Knowledge Graph**: Entity and relationship extraction for technical components
- **Multi-Source Synthesis**: Cross-document reasoning with citation aggregation
- **Source Traceability**: Every answer includes inline citations with page references
- **IAI Branding**: Custom interface for Israel Aerospace Industries evaluation

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS, Better Auth |
| Backend | FastAPI, Python 3.11 |
| Vector Search | txtai with OpenAI embeddings |
| Graph Database | FalkorDB |
| Document Processing | Docling |
| LLM | OpenAI GPT-5-mini |
| Reranking | DeepInfra Qwen3-Reranker |
| Deployment | Docker Compose, Caddy (HTTPS) |

## Quickstart

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- DeepInfra API key (for reranking)

### Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ironmind
   ```

2. Copy environment template:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Start services:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Production Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Hetzner VPS deployment instructions.

## Project Structure

```
ironmind/
├── frontend/           # Next.js frontend application
│   ├── app/           # App router pages
│   ├── components/    # Shared React components
│   └── lib/           # Utilities and API client
├── backend/           # FastAPI backend application
│   ├── app/
│   │   ├── routers/   # API endpoints
│   │   ├── services/  # Business logic
│   │   ├── models/    # Pydantic schemas
│   │   └── core/      # Database, logging
├── infra/             # Infrastructure configuration
│   ├── docker-compose.prod.yml
│   └── Caddyfile
├── docs/              # Documentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── PIPELINE_DESIGN.md
│   └── EXAMPLE_QUERIES.md
└── docker-compose.yml # Local development
```

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System components and data flow
- [Deployment Guide](docs/DEPLOYMENT.md) - Local and production setup
- [Pipeline Design](docs/PIPELINE_DESIGN.md) - RAG pipeline, chunking, knowledge graph
- [Example Queries](docs/EXAMPLE_QUERIES.md) - Sample Q&A with explanations

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents/upload` | POST | Upload a document |
| `/api/documents` | GET | List user's documents |
| `/api/documents/{id}/status` | GET | Get processing status |
| `/api/chat` | POST | Ask a question |
| `/health` | GET | Service health check |

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- Built for Israel Aerospace Industries (IAI) POC evaluation
- Powered by OpenAI, DeepInfra, and open-source RAG technologies

---

**Note**: This is a Proof of Concept system. Not intended for production use with classified or sensitive data.
