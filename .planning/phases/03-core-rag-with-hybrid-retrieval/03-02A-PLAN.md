---
phase: 03-core-rag-with-hybrid-retrieval
plan: 02A
type: execute
wave: 2
depends_on: ["03-01"]
files_modified:
  - backend/app/services/indexer.py
autonomous: true

must_haves:
  truths:
    - "Indexer initializes with hybrid=True for combined semantic+BM25 search"
    - "Indexer uses OpenAI text-embedding-3-small embeddings when API key is available"
    - "hybrid_search method returns chunks with both semantic and BM25 scores"
    - "Search results filter by user_id at query level for multi-tenant isolation"
    - "Re-indexing same document deletes old chunks before adding new ones (no duplication)"
  artifacts:
    - path: "backend/app/services/indexer.py"
      provides: "Hybrid search capability"
      contains: "hybrid_search"
      min_lines: 120
  key_links:
    - from: "backend/app/services/indexer.py"
      to: "txtai.Embeddings"
      via: "hybrid=True config"
      pattern: "hybrid.*True"
    - from: "backend/app/services/indexer.py"
      to: "backend/app/config.py"
      via: "settings.OPENAI_API_KEY"
      pattern: "OPENAI_API_KEY|OPENAI_EMBEDDING_MODEL"
---

<objective>
Add hybrid search capability to TxtaiIndexer with OpenAI embeddings.

Purpose: Enable dual-channel retrieval (semantic + BM25) for technical documents where both meaning and exact terms matter.
Output: Updated indexer.py with hybrid_search method, OpenAI embedding support, and de-duplication on re-ingestion
</objective>

<execution_context>
@C:\Users\Omer\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\Omer\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-core-rag-with-hybrid-retrieval/03-RESEARCH.md
@.planning/phases/03-core-rag-with-hybrid-retrieval/03-CONTEXT.md
@.planning/phases/03-core-rag-with-hybrid-retrieval/03-01-SUMMARY.md
@backend/app/services/indexer.py
@backend/app/config.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enable hybrid search in TxtaiIndexer</name>
  <files>backend/app/services/indexer.py</files>
  <action>
Update backend/app/services/indexer.py to enable hybrid search:

**Modify _initialize_embeddings() config:**

```python
def _initialize_embeddings(self):
    """Initialize txtai embeddings with hybrid search and OpenAI embeddings."""
    # Use OpenAI embeddings if API key available, fallback to local model
    if settings.OPENAI_API_KEY:
        embedding_path = f"openai/{settings.OPENAI_EMBEDDING_MODEL}"
        logger.info("using_openai_embeddings", model=settings.OPENAI_EMBEDDING_MODEL)
    else:
        embedding_path = "sentence-transformers/all-MiniLM-L6-v2"
        logger.warning("openai_key_missing", fallback="sentence-transformers/all-MiniLM-L6-v2")

    config = {
        "path": embedding_path,
        "content": True,  # Store metadata - CRITICAL
        "backend": "sqlite",
        "hybrid": True,  # Enable hybrid search (semantic + BM25)
        "scoring": {
            "method": "bm25",
            "normalize": True  # REQUIRED for RRF fusion - normalizes BM25 scores to 0-1
        }
    }
    # ... rest of initialization
```

**IMPORTANT - RRF Verification:**
txtai's hybrid search with `normalize: True` uses score normalization that enables proper RRF fusion.
The `weights` parameter in search controls the semantic/BM25 balance:
- weights=0.5 means 50% semantic, 50% BM25 (equal weight)
- txtai internally applies fusion via normalized score combination

Verify by checking txtai documentation: hybrid search with normalized BM25 scores produces RRF-equivalent ranking.

**Add hybrid_search method:**

```python
def hybrid_search(
    self,
    query: str,
    user_id: str,
    limit: int = 25,
    weights: float = 0.5,  # 0.5 = equal semantic/BM25
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Hybrid search combining semantic and BM25 with user filtering.

    Uses txtai's built-in hybrid search with normalized score fusion.
    Score normalization (scoring.normalize=True) enables proper fusion
    equivalent to Reciprocal Rank Fusion (RRF).

    Args:
        query: Search query
        user_id: User ID for filtering (multi-tenant isolation)
        limit: Max results to return
        weights: Semantic/BM25 balance (0=BM25 only, 1=semantic only, 0.5=equal)
        threshold: Minimum score to include (filters low-relevance results)

    Returns:
        List of chunks with scores and full metadata
    """
    if not self.embeddings:
        logger.warning("embeddings_not_initialized")
        return []

    try:
        # Execute hybrid search with weights parameter
        # txtai handles fusion internally when hybrid=True
        results = self.embeddings.search(
            query,
            limit=limit * 2,  # Fetch more for post-filtering
            weights=weights
        )

        # Filter by user_id and threshold
        filtered = []
        for result in results:
            if result.get("user_id") != user_id:
                continue
            score = result.get("score", 0)
            if score < threshold:
                continue
            filtered.append({
                "chunk_id": result.get("id"),
                "text": result.get("text"),
                "doc_id": result.get("doc_id"),
                "filename": result.get("filename"),
                "page_range": result.get("page_range"),
                "section_title": result.get("section_title"),
                "score": score,
                "user_id": user_id
            })

        # Limit to requested count
        return filtered[:limit]

    except Exception as e:
        logger.error("hybrid_search_failed", error=str(e), user_id=user_id)
        return []
```
  </action>
  <verify>
python -c "from app.services.indexer import TxtaiIndexer; idx = TxtaiIndexer(); print('hybrid_search exists:', hasattr(idx, 'hybrid_search')); print('config hybrid:', idx.embeddings.config.get('hybrid', False) if idx.embeddings else 'N/A')"
  </verify>
  <done>
TxtaiIndexer has hybrid=True in config and hybrid_search method that combines semantic+BM25 with user filtering
  </done>
</task>

<task type="auto">
  <name>Task 2: Ensure de-duplication on re-ingestion (INDEX-05)</name>
  <files>backend/app/services/indexer.py</files>
  <action>
Verify and document that re-ingesting a document updates cleanly without duplication.

**Current state:** The indexer already has `delete_document_chunks(doc_id)` method.

**Ensure proper integration:**
The document pipeline (from Phase 2) should call `delete_document_chunks` before `index_chunks` when re-ingesting.

Add a convenience method to make this explicit:

```python
def reindex_document(
    self,
    chunks: List[ChunkMetadata],
    user_id: str,
    doc_id: str
) -> int:
    """
    Re-index a document, removing old chunks first.

    Ensures INDEX-05: Re-ingesting same document updates cleanly without duplication.

    Args:
        chunks: New chunks to index
        user_id: User ID
        doc_id: Document ID

    Returns:
        Number of chunks indexed
    """
    # Delete existing chunks for this document
    deleted = self.delete_document_chunks(doc_id)
    if deleted > 0:
        logger.info("old_chunks_deleted", doc_id=doc_id, count=deleted)

    # Index new chunks
    indexed = self.index_chunks(chunks, user_id, doc_id)

    logger.info("document_reindexed",
               doc_id=doc_id,
               deleted=deleted,
               indexed=indexed)

    return indexed
```

**Update delete_document_chunks to be more robust:**
Ensure it handles the case where hybrid search is enabled and both semantic and BM25 indices are cleared.
  </action>
  <verify>
python -c "from app.services.indexer import TxtaiIndexer; idx = TxtaiIndexer(); print('reindex_document exists:', hasattr(idx, 'reindex_document')); print('delete_document_chunks exists:', hasattr(idx, 'delete_document_chunks'))"
  </verify>
  <done>
reindex_document method exists and calls delete_document_chunks before index_chunks to prevent duplication
  </done>
</task>

</tasks>

<verification>
1. Indexer initializes with hybrid=True: Check config in logs or debugger
2. hybrid_search method exists and accepts query, user_id, limit, weights, threshold
3. reindex_document method exists and prevents duplication
4. OpenAI embeddings used when OPENAI_API_KEY is set
5. BM25 scoring has normalize=True for proper fusion
</verification>

<success_criteria>
- TxtaiIndexer._initialize_embeddings() sets hybrid=True
- TxtaiIndexer._initialize_embeddings() sets scoring.normalize=True (required for RRF-equivalent fusion)
- TxtaiIndexer.hybrid_search() accepts query, user_id, limit, weights, threshold
- TxtaiIndexer.hybrid_search() filters by user_id at query level
- TxtaiIndexer.hybrid_search() filters by threshold score
- TxtaiIndexer.reindex_document() deletes old chunks before indexing new ones
- OpenAI embeddings used when API key available, local fallback otherwise
</success_criteria>

<output>
After completion, create `.planning/phases/03-core-rag-with-hybrid-retrieval/03-02A-SUMMARY.md`
</output>
