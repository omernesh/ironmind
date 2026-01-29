---
phase: 05-multi-source-synthesis
plan: 01
subsystem: multi-source-synthesis
tags: [document-relationships, graph-storage, multi-source, schemas, citation-models]

# Dependency Graph
requires: [04-05]  # Knowledge graph debug endpoints
provides: [doc-relationship-schemas, doc-relationship-store, multi-source-citation-model]
affects: [05-02, 05-03, 05-04]  # Document cross-ref detection, synthesis pipeline, debug endpoints

# Technical Stack
tech-stack:
  added:
    - python-Levenshtein>=0.25.0
    - networkx>=3.0
  patterns:
    - document-level-graph-storage
    - multi-source-citation-tracking
    - pydantic-literal-constraints

# File Tracking
key-files:
  created:
    - backend/app/services/graph/doc_relationships.py
    - .planning/phases/05-multi-source-synthesis/05-01-SUMMARY.md
  modified:
    - backend/app/services/graph/schemas.py
    - backend/app/services/graph/__init__.py
    - backend/app/models/chat.py
    - backend/requirements.txt

# Decisions & Outcomes
decisions:
  - id: DOC_REL_SCHEMA
    choice: "Literal type constraint for relationship_type (explicit_citation | shared_entities)"
    rationale: "Enforces schema validation, prevents invalid relationship types, matches entity graph pattern from Phase 4"
    alternatives: ["String enum", "Free-form string"]

  - id: EDGE_TYPES
    choice: "Separate CITES and SHARES_ENTITIES edge types in FalkorDB"
    rationale: "Enables filtering by relationship type, weighted scoring (explicit citations = 1.0, shared = 0.5-0.9)"
    alternatives: ["Single RELATES_TO edge with type property"]

  - id: MULTI_SOURCE_FIELDS
    choice: "Add multi_source boolean + related_doc_ids to Citation model"
    rationale: "Minimal schema extension, enables compact notation detection, tracks document relationships without breaking existing code"
    alternatives: ["Separate MultiSourceCitation subclass", "Post-processing citation lists"]

# Metrics
metrics:
  duration: 382s  # ~6 minutes
  completed: 2026-01-29
---

# Phase 05 Plan 01: Document Relationship Schemas & Storage Summary

Document relationship graph foundation for multi-source synthesis with FalkorDB storage, Pydantic schemas, and extended citation models.

## What Was Built

### 1. DocumentRelationship Pydantic Schema
**File:** `backend/app/services/graph/schemas.py`

Added DocumentRelationship model with:
- `source_doc_id` / `target_doc_id` for document linkage
- `relationship_type` with Literal constraint ("explicit_citation" | "shared_entities")
- `strength` score (0.0-1.0) with validation
- `evidence` list for citation text or shared entity names

**Purpose:** Type-safe document relationship representation for graph storage

### 2. DocumentRelationshipStore Class
**File:** `backend/app/services/graph/doc_relationships.py` (230 lines)

Implemented FalkorDB document relationship graph with:
- **Document nodes:** doc_id, filename, user_id, page_count, chunk_count
- **Edge types:** CITES (explicit citations), SHARES_ENTITIES (implicit via shared entities)
- **CRUD operations:**
  - `add_document_node()`: Create/update document nodes
  - `add_relationship()`: Create weighted relationships with evidence
  - `get_related_documents()`: Query expansion for multi-doc retrieval
  - `get_all_relationships()`: Debug endpoint support
  - `delete_document_relationships()`: Re-ingestion cleanup
  - `count_relationships()`: Metrics by type

**Pattern:** Reuses FalkorDB connection from GraphStore, follows same user isolation and indexing patterns

### 3. Extended Citation Model
**File:** `backend/app/models/chat.py`

Added multi-source synthesis fields:
- `Citation.multi_source`: Boolean flag for multi-source claims (adjacent citations)
- `Citation.related_doc_ids`: List of related documents from relationship graph
- `ChatResponse.synthesis_mode`: Indicates multi-document synthesis activation
- `ChatResponse.source_doc_count`: Tracks distinct source document count

**Backward compatible:** Defaults ensure existing code continues working

### 4. New Dependencies
**File:** `backend/requirements.txt`

- `python-Levenshtein>=0.25.0`: Fast fuzzy string matching for citation detection
- `networkx>=3.0`: Graph algorithms for document relationship scoring

## Technical Decisions

### Literal Type Constraints
Used Pydantic `Literal["explicit_citation", "shared_entities"]` for relationship_type:
- Catches invalid types at validation time
- Provides IDE autocomplete
- Matches pattern from Phase 4 Entity/Relationship schemas
- Alternative (string enum) would require extra validation layer

### Separate Edge Types in FalkorDB
Created distinct CITES and SHARES_ENTITIES edge types:
- Enables type-specific queries (`MATCH (a)-[:CITES]->(b)`)
- Weighted scoring: Explicit citations = 1.0, shared entities = 0.5-0.9
- Clearer semantics than single RELATES_TO edge with type property

### Multi-Source Fields in Citation Model
Extended existing Citation model vs. creating new subclass:
- Minimal schema change reduces integration work
- Defaults (multi_source=False) ensure backward compatibility
- related_doc_ids enables UI to show "related documents" without graph queries
- Alternative (separate MultiSourceCitation) would complicate generator.py integration

## Verification Results

All success criteria met:

1. ✅ DocumentRelationship Pydantic schema exists with Literal relationship_type constraint
2. ✅ DocumentRelationshipStore class provides CRUD for document relationships in FalkorDB
3. ✅ Citation model includes multi_source boolean field
4. ✅ ChatResponse model includes synthesis_mode and source_doc_count fields
5. ✅ New dependencies (python-Levenshtein, networkx) added to requirements.txt

**Import verification:**
```bash
python -c "from app.services.graph import DocumentRelationshipStore; from app.services.graph.schemas import DocumentRelationship"
# All imports OK

python -c "from app.models.chat import Citation; c = Citation(..., multi_source=True); print(c.multi_source)"
# True

python -c "from app.services.graph.schemas import DocumentRelationship; r = DocumentRelationship(source_doc_id='a', target_doc_id='b', relationship_type='explicit_citation', strength=1.0); print(r.relationship_type)"
# explicit_citation
```

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Ready for 05-02 (Document Cross-Reference Detection):**
- DocumentRelationship schema ready for relationship extraction
- DocumentRelationshipStore.add_relationship() ready to persist detected relationships
- DocumentRelationshipStore.add_document_node() ready for pipeline integration

**Ready for 05-03 (Multi-Source Synthesis):**
- Citation.multi_source field ready for compact notation detection
- ChatResponse.synthesis_mode ready for multi-doc activation tracking
- Citation.related_doc_ids ready for relationship metadata

**Ready for 05-04 (Debug Endpoints):**
- DocumentRelationshipStore.get_all_relationships() ready for debug API
- DocumentRelationshipStore.count_relationships() ready for metrics endpoint

**Foundation complete:**
- FalkorDB schema supports both entity graph (Phase 4) and document relationship graph (Phase 5)
- Citation model extensible for future synthesis features
- Pydantic validation prevents invalid relationship data

## Performance Notes

- **Duration:** 382 seconds (~6 minutes)
- **Files created:** 2 (doc_relationships.py, SUMMARY.md)
- **Files modified:** 4 (schemas.py, __init__.py, chat.py, requirements.txt)
- **Lines added:** ~280

**Fast execution:** Schema-only work with no external service dependencies

## Commits

| Task | Commit | Description | Files |
|------|--------|-------------|-------|
| 1 | 064b6f0 | Add DocumentRelationship schema | schemas.py |
| 2 | 4f2f618 | Create DocumentRelationshipStore | doc_relationships.py, __init__.py |
| 3 | 3096ab4 | Extend Citation model with multi-source fields | chat.py, requirements.txt |

**All commits:** Small, atomic, independently revertable

## Future Integration Points

**Plan 05-02 will:**
- Import DocumentRelationshipStore in pipeline.py
- Call add_document_node() during ingestion
- Detect explicit citations using python-Levenshtein fuzzy matching
- Detect shared entities using existing GraphStore
- Call add_relationship() for discovered document links

**Plan 05-03 will:**
- Check ChatResponse.source_doc_count to activate synthesis mode
- Set Citation.multi_source=True for adjacent citations
- Use get_related_documents() for query expansion
- Populate Citation.related_doc_ids for UI metadata

**Plan 05-04 will:**
- Create GET /api/debug/doc-relationships endpoint
- Use get_all_relationships() and count_relationships()
- Format output for graph visualization (edgelist/cytoscape)

---

*Phase: 05-multi-source-synthesis*
*Plan: 01 of 4*
*Duration: ~6 minutes*
*Status: Complete - Foundation ready for cross-reference detection*
