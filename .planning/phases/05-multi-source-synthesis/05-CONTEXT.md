# Phase 5: Multi-Source Synthesis - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the RAG system to reason across multiple documents, detect cross-references between documents, build document relationship graphs, and synthesize comprehensive answers from 2+ sources with transparent citation aggregation. This phase builds on Phase 4's knowledge graph to enable multi-document reasoning without adding new user-facing features.

</domain>

<decisions>
## Implementation Decisions

### Cross-reference detection
- Cross-reference signals: Explicit citations (bibliographic references, "See Document X", hyperlinks) PLUS shared entities from knowledge graph
- Prioritization: Explicit citations are stronger signals than shared entities — weight explicit references higher in document relationship scoring
- Shared entity threshold: Require 2+ shared entities to establish a cross-reference (single shared entity is insufficient)
- Storage strategy: Pre-compute and store document relationships during ingestion — build persistent document relationship graph for faster queries and explicit debug endpoints

### Synthesis strategy
- Answer structure: Topic-organized format — group information by subtopics with multi-source support per topic for complex answers
- Activation threshold: Require 2+ distinct documents to trigger synthesis mode — single-document queries use standard RAG pipeline
- Consensus indicators: Use subtle language ("consistently", "multiple sources mention", "according to multiple documents") without exact source counts
- Claude's Discretion: Conflict handling when documents disagree — determine best approach based on query context and confidence

### Citation presentation
- Multi-source format: Compact notation for 3+ sources — [1-3: Doc A p.5, Doc B p.12, Doc C p.8]
- Snippet preview: Show most relevant snippet only (from highest-ranked source) — avoid overwhelming detail from all sources
- Source transparency: Unified presentation — treat document-stated and graph-derived information equally without distinction
- Citation ordering: By retrieval rank — order citations by relevance score from retrieval/reranking pipeline

### Entity resolution scope
- Merge aggressiveness: Conservative approach — only merge entities with exact name matches or explicit aliases to avoid false positives
- Acronym handling: Store both forms — merge entities with acronym expansion but preserve both acronym and expanded forms as aliases
- Conflicting attributes: Merge and track source — combine entity attributes from multiple documents but track which document contributed each attribute for provenance
- Resolution timing: During ingestion — perform entity resolution when documents are uploaded for pre-computed graph and consistent results

</decisions>

<specifics>
## Specific Ideas

- Document relationship graph should support debug endpoint inspection (similar to Phase 4's /api/debug/graph endpoints)
- Build on existing ACRONYM_MAP from Phase 4 for entity resolution
- Entity attribute provenance enables answering questions like "which document describes X as having property Y?"
- Topic-organized answers should maintain clear section headers for each subtopic

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-multi-source-synthesis*
*Context gathered: 2026-01-29*
