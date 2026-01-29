# IRONMIND Pipeline Design

## Overview

IRONMIND uses a multi-stage RAG pipeline optimized for technical documentation:

1. **Document Processing** - Parse, chunk, extract entities
2. **Hybrid Retrieval** - Semantic + keyword search with RRF fusion
3. **Graph Enhancement** - Entity relationships and document links
4. **Reranking** - Cross-encoder precision boost
5. **Generation** - Grounded answer synthesis with citations

## Document Processing Pipeline

### Stage 1: Parsing (Docling)

Docling extracts structured content preserving:
- Section headings and hierarchy
- Page numbers and boundaries
- Tables and lists
- Inline formatting

Output: Markdown with metadata annotations

### Stage 2: Semantic Chunking

Unlike fixed-size chunking, semantic chunking:
- Respects section boundaries (never splits mid-section)
- Targets ~1000 tokens per chunk with 15% overlap
- Merges small sections (<50 tokens)
- Splits large sections at paragraph boundaries

Chunk metadata includes:
- doc_id, user_id (isolation)
- page_range, section_title (traceability)
- SHA-256 hash (deduplication)

### Stage 3: Entity Extraction

LLM (GPT-4o with Structured Outputs) extracts:

**Entity Types:**
- hardware, software, configuration, error

**Relationship Types:**
- depends_on, configures, connects_to, is_part_of

Extraction uses schema-constrained generation for 100% valid output.

### Stage 4: Document Relationships

Cross-reference detection finds document links:

**Explicit Citations:**
- Document code patterns (e.g., "FC-001-234")
- "See Document X" patterns
- Section references

**Shared Entities:**
- Documents sharing 2+ entities are linked
- Strength based on entity count (0.5 - 0.9)

### Stage 5: Indexing

txtai index with:
- OpenAI text-embedding-3-small embeddings
- BM25 sparse index for keyword matching
- SQLite backend for persistence
- User-based filtering for multi-tenancy

## Query Processing Pipeline

### Stage 1: Hybrid Retrieval

**Semantic Search:**
- Query embedded with same model (text-embedding-3-small)
- Cosine similarity against indexed chunks
- Returns top-25 by score

**BM25 Search:**
- Keyword matching with TF-IDF weighting
- Good for technical terms, acronyms, codes
- Returns top-25 by score

**Reciprocal Rank Fusion (RRF):**
```
score(d) = Σ 1/(k + rank_i(d))
```
Where k=60 (standard), combining both result sets.

### Stage 2: Graph Enhancement

For relationship queries (detected via keywords like "connect", "depend"):

1. Extract entities from query
2. Retrieve related entities from graph (depth=2)
3. Fetch chunks mentioning those entities
4. Merge with semantic results (deduplicated)

### Stage 3: Document Expansion

If related documents exist (via cross-references):

1. Find top-2 related docs (min_strength=0.5)
2. Retrieve additional chunks from related docs
3. Merge into result set

### Stage 4: Reranking

DeepInfra Qwen3-Reranker-0.6B:
- Cross-encoder scores query-document pairs
- More accurate than bi-encoder similarity
- 30-50% precision improvement
- Returns top-12

### Stage 5: Generation

GPT-5-mini with grounding prompt:

**System Prompt:**
- Answer ONLY from provided documents
- Use [N] citations inline
- Acknowledge uncertainty
- For multi-source: organize by topic, note consensus/disagreement

**Context Format:**
```
[1: filename.docx, p.12-14]
<chunk text>

[2: filename.docx, p.23]
<chunk text>
```

**Multi-Source Synthesis:**
Activated when:
- 2+ documents in context
- 2+ chunks per document

Uses topic-organized prompting for cross-document patterns.

## Performance Characteristics

| Stage | Typical Latency | Notes |
|-------|-----------------|-------|
| Retrieval | 50-100ms | txtai + BM25 fusion |
| Expansion | 20-50ms | Graph queries |
| Reranking | 100-200ms | DeepInfra API call |
| Generation | 500-2000ms | OpenAI API call |
| **Total** | **1-3 seconds** | Target: <10s |

## Quality Metrics

- **Retrieval**: Recall@25 (are relevant docs retrieved?)
- **Reranking**: Precision@10 (are top results relevant?)
- **Generation**: Faithfulness (answers grounded in sources?)
- **Citations**: Traceability (can user verify claims?)

## Configuration

Key settings in `backend/app/config.py`:

```python
RETRIEVAL_LIMIT = 25      # Initial retrieval
RERANK_LIMIT = 12         # After reranking
CONTEXT_LIMIT = 10        # Sent to LLM
HYBRID_WEIGHT = 0.5       # Semantic vs BM25
MIN_SIMILARITY = 0.5      # Score threshold
```
