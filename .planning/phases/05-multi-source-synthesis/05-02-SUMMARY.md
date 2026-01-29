---
phase: 05-multi-source-synthesis
plan: 02
subsystem: graph
tags: [falkordb, cross-reference-detection, document-relationships, pattern-matching, fuzzy-matching]

# Dependency graph
requires:
  - phase: 05-01
    provides: DocumentRelationship schema and DocumentRelationshipStore for graph storage
  - phase: 04-02
    provides: EntityExtractor and entity graph for shared entity detection
  - phase: 02-04
    provides: DocumentPipeline orchestration pattern
provides:
  - CrossReferenceDetector service with dual-signal relationship detection
  - Automated document relationship extraction during ingestion
  - Explicit citation detection via regex patterns (doc codes, "See Document X", section refs)
  - Shared entity detection with 2+ common entities threshold
  - Document relationship graph populated in FalkorDB
affects: [05-03-multi-source-synthesis, 05-04-synthesis-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dual-signal cross-reference detection (explicit citations + shared entities)
    - Priority-based relationship scoring (explicit 1.0 > shared entities 0.5-0.9)
    - Fuzzy matching with Levenshtein ratio for citation text comparison
    - Graceful degradation pattern for relationship extraction failures

key-files:
  created:
    - backend/app/services/graph/cross_reference.py
  modified:
    - backend/app/services/pipeline.py
    - backend/app/services/graph/graph_store.py
    - backend/app/services/graph/__init__.py
    - backend/app/core/database.py
    - backend/app/models/documents.py

key-decisions:
  - "Explicit citations prioritized over shared entities (skip shared if explicit exists)"
  - "Fuzzy matching with 70% similarity threshold for citation text vs filename matching"
  - "Shared entity strength scoring: 0.5 base + 0.1 per entity beyond 2, capped at 0.9"
  - "Document relationships extracted only against DONE documents (skip Processing/Failed)"
  - "Relationship extraction failures don't crash pipeline (logged as warning, continue to indexing)"

patterns-established:
  - "Dual-signal cross-reference detection: Pattern 1 (strong signal) + Pattern 2 (weak signal) with deduplication"
  - "Document relationship extraction as pipeline stage 3.5 (between graph extraction and indexing)"
  - "Graceful enhancement pattern: graph features log warnings on failure but don't block core functionality"

# Metrics
duration: 5min
completed: 2026-01-29
---

# Phase 05 Plan 02: Document Cross-Reference Detection Summary

**Automated document relationship detection during ingestion using dual-signal approach: explicit citations (regex patterns) + shared entities (2+ threshold)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-29T12:48:24Z
- **Completed:** 2026-01-29T12:53:33Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- CrossReferenceDetector service with dual-signal detection (explicit citations + shared entities)
- Explicit citation detection using 3 regex patterns (doc codes, "See Document X", section references)
- Shared entity detection comparing 2+ common entities across documents with acronym expansion
- Document relationship extraction integrated into pipeline as stage 3.5 (after graph extraction, before indexing)
- Fuzzy matching with 70% Levenshtein similarity for citation text vs filename comparison
- Priority-based deduplication (explicit citations take precedence over shared entities)
- Document relationship graph automatically populated during ingestion

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CrossReferenceDetector service** - `1cc5d54` (feat)
   - CrossReferenceDetector class with detect_cross_references, _detect_explicit_references, _detect_shared_entities methods
   - Added list_entities_for_doc method to GraphStore for entity comparison
   - Exported CrossReferenceDetector from graph services module

2. **Task 2: Integrate document relationship extraction into pipeline** - `f79b56a` (feat)
   - Added DocumentRelationships stage after GraphExtracting (before Indexing)
   - Pipeline detects cross-references for each new document against existing DONE documents
   - Added doc_relationship_count field to Document model for metrics tracking
   - Updated STAGE_WEIGHTS to include DocumentRelationships (5% weight)

## Files Created/Modified

- `backend/app/services/graph/cross_reference.py` - CrossReferenceDetector service with dual-signal detection
- `backend/app/services/graph/graph_store.py` - Added list_entities_for_doc method for entity comparison
- `backend/app/services/graph/__init__.py` - Exported CrossReferenceDetector
- `backend/app/services/pipeline.py` - Integrated document relationship extraction stage
- `backend/app/core/database.py` - Added list_user_documents alias method
- `backend/app/models/documents.py` - Added doc_relationship_count field

## Decisions Made

**1. Explicit citations prioritize over shared entities**
- Rationale: Explicit citations are stronger signals (author explicitly referenced document). If explicit citation exists to target doc, skip adding weaker shared entity relationship to avoid redundancy.

**2. Fuzzy matching with 70% similarity threshold**
- Rationale: Citation text in documents often doesn't exactly match filename (abbreviations, version numbers). Levenshtein ratio with 70% threshold balances precision/recall for document code matching.

**3. Shared entity strength scoring formula**
- Rationale: Base 0.5 strength for 2 shared entities, increase by 0.1 per additional entity (capped at 0.9). Provides gradient of confidence based on entity overlap without reaching explicit citation strength (1.0).

**4. Only detect relationships against DONE documents**
- Rationale: Documents in Processing/Failed status have incomplete entity graphs. Comparing against incomplete data would produce false negatives. Filter for status == DONE ensures complete entity sets.

**5. Graceful error handling for relationship extraction**
- Rationale: Document relationships are enhancement, not critical path. If detection fails (FalkorDB unavailable, API error), log warning but continue to indexing stage. Core document ingestion should not fail due to relationship extraction issues.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly. All patterns and integrations worked as designed.

## User Setup Required

None - no external service configuration required. Uses existing FalkorDB connection from phase 04.

## Next Phase Readiness

**Ready for 05-03 (Multi-Source Synthesis Pipeline):**
- Document relationship graph populated during ingestion
- CrossReferenceDetector provides both explicit citations and shared entity relationships
- Relationship strength scores available for prioritization in synthesis
- Document nodes include metadata (filename, page_count, chunk_count) for citation formatting

**Ready for 05-04 (Synthesis Verification & Debug):**
- doc_relationship_count tracked in Document model for metrics
- DocumentRelationshipStore provides get_related_documents() for querying relationship graph
- Relationship evidence stored (citation text or shared entity names) for debugging

**No blockers or concerns.** Document relationship detection integrated cleanly into pipeline. Dual-signal approach provides both high-confidence explicit citations and broader shared entity relationships for comprehensive multi-source synthesis.

---
*Phase: 05-multi-source-synthesis*
*Completed: 2026-01-29*
