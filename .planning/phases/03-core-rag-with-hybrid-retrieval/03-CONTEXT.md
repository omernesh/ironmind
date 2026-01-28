# Phase 3: Core RAG with Hybrid Retrieval - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

End-to-end RAG query pipeline that retrieves relevant chunks from technical documents using hybrid search (semantic + BM25), reranks with Mistral, and generates answers with source citations using GPT-5-mini. Users ask natural language questions and receive grounded answers with transparent traceability to source documents.

</domain>

<decisions>
## Implementation Decisions

### Retrieval Strategy

**Initial Retrieval:**
- Retrieve 20-30 chunks from txtai before reranking (balanced performance ~2-3s)
- Equal weight (50/50) for semantic vs BM25 hybrid search
- Apply relevance threshold to discard low-scoring chunks
- Always filter chunks to current user's documents only (user_id scoping)
- Support full metadata filtering (filename, upload date, doc type)

**Query Processing:**
- Advanced preprocessing: expand common aerospace acronyms, fix typos, rephrase for clarity
- Cache full results for 5-10 minutes for repeated queries

**Reranking:**
- Always apply Mistral reranking (consistent quality boost, ~1-2s latency)
- Send top 10-15 retrieved chunks to reranker (balances quality and speed)
- Send top 8-10 reranked chunks to GPT-5-mini for answer generation

**No Results Handling:**
- Return 'no answer found' when no chunks meet relevance threshold
- Prevents hallucination, suggests query refinement

**Diagnostics:**
- Log full pipeline metrics: query, retrieved chunk IDs, semantic scores, BM25 scores, RRF ranks, reranker scores, final selection, latencies per stage

### Citation & Source Display

- Each citation includes: doc name + page + snippet (e.g., `[Doc: manual.pdf, p.42, '...error code 0x1234...']`)
- Format: Footnote numbers `[1], [2]` in answer text, detailed list at bottom
- Separate footnotes for each chunk, even from same document (e.g., `[1: manual.pdf p.42]`, `[2: manual.pdf p.58]`)
- Return citations as structured JSON format for frontend interactivity (Phase 6 can make them clickable/expandable)

### Answer Generation Tone

- **Technical depth:** Match document style - mirror the technical level of source documents
- **Uncertainty:** Explicit uncertainty language (e.g., "Based on available documents, X... However, Y is not covered")
- **Length:** Concise (2-4 sentences) - direct answer with key facts
- **Tone:** Professional/formal - clear, factual, no filler
- **Conflicts:** Acknowledge when sources disagree (e.g., "Source A states X [1], while Source B indicates Y [2]")
- **Confidence:** No explicit confidence scores - implicit in language
- **Formatting:** Use Markdown for code snippets, formulas, tables (```code```, **bold**, etc.)
- **Content:** Facts only - no actionable recommendations beyond source text

### Multi-Source Synthesis

- **Merging:** Synthesize with attribution (e.g., "Documents A and B both describe X. A states Y [1], B adds Z [2]")
- **Complementary info:** Integrated answer (e.g., "X is described in [1]. Additionally, Y is noted in [2], and Z in [3]")
- **Prioritization:** Use reranker score - highest relevance gets primary position
- **Consensus:** Explicit indicators (e.g., "All sources agree X" vs "According to [1], X")

</decisions>

<specifics>
## Specific Ideas

- System should feel like querying a technical knowledge base - accuracy and traceability over conversational polish
- Citations are critical for defense/aerospace documentation - every claim must be traceable
- Performance target: <10 seconds end-to-end (target 5-8s)
- System must handle 2-3 concurrent users without degradation

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 03-core-rag-with-hybrid-retrieval*
*Context gathered: 2026-01-28*
