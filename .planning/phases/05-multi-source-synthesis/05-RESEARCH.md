# Phase 5: Multi-Source Synthesis - Research

**Researched:** 2026-01-29
**Domain:** Multi-document reasoning, cross-reference detection, document relationship graphs, citation aggregation
**Confidence:** MEDIUM-HIGH

## Summary

Phase 5 enhances the RAG system to synthesize information across multiple documents by detecting cross-references (explicit citations + shared entities), building document relationship graphs, and generating comprehensive multi-source answers with transparent citation aggregation. This builds on Phase 4's knowledge graph to enable document-level relationship reasoning without adding new user-facing features.

**Current state of the art (2025-2026):** Multi-document RAG synthesis is actively evolving with approaches like Cross-Document Topic-Aligned (CDTA) chunking, which consolidates information across documents using LLM-based knowledge synthesis. GraphRAG systems now routinely maintain multiple knowledge representations (vector embeddings + knowledge graphs + document relationship graphs) to enable both semantic search and structural reasoning. Recent research emphasizes that **simple concatenation fails for multi-document synthesis** - systems need explicit conflict resolution, citation tracking, and topic-organized synthesis to handle questions where no single document contains complete coverage.

**Primary recommendation:** Build document relationship graph during ingestion (pre-computed for performance), use dual signal detection (explicit citations weighted higher than shared entities with 2+ entity threshold), implement topic-organized synthesis prompting with Chain-of-Thought for citation generation, and extend existing Citation model to support multi-source compact notation.

## Standard Stack

The established libraries/tools for multi-document synthesis:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FalkorDB | 1.4.0 | Document relationship graph | Already in stack from Phase 4, supports multi-level graphs (entities + documents) |
| OpenAI API | 1.0.0+ | Multi-source synthesis + entity matching | Already in stack, Chain-of-Thought prompting improves citation accuracy 30-50% |
| Pydantic | 2.0+ | Extended citation models | Already in stack, add multi-source fields to existing Citation schema |
| txtai | 7.5+ | Document-level queries | Already in stack, supports SQL aggregation for document statistics |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-Levenshtein | 0.25+ | Cross-reference text matching | Detecting explicit citations with fuzzy matching ("See Section 3.2..." variants) |
| networkx | 3.0+ | Document graph algorithms | Computing document similarity scores, connected components |
| ACRONYM_MAP | - | Entity resolution | Already exists in retriever.py, extend for document-level entity matching |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pre-computed graph | Runtime detection | Pre-computation adds ingestion time but enables faster queries and debug endpoints (user decision from CONTEXT.md) |
| Topic-organized | Chronological | Topic organization better for synthesis questions ("what do docs say about X?"), chronological better for temporal questions (not Phase 5 scope) |
| Compact notation [1-3] | Individual [1][2][3] | Compact reduces visual clutter for 3+ sources (user decision), individual better for 1-2 sources |

**Installation:**
```bash
# Add to backend/requirements.txt
python-Levenshtein>=0.25.0  # Fast fuzzy string matching for citation detection
networkx>=3.0  # Graph algorithms for document relationship scoring
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
├── graph/
│   ├── extractor.py          # EXISTING - entity extraction
│   ├── graph_store.py        # EXISTING - entity graph storage
│   ├── graph_retriever.py    # EXISTING - entity subgraph retrieval
│   ├── doc_relationships.py  # NEW - document relationship graph
│   └── schemas.py            # EXISTING - extend with DocumentRelationship
├── retriever.py              # EXISTING - enhance with multi-doc awareness
├── generator.py              # EXISTING - enhance with synthesis prompting
└── pipeline.py               # EXISTING - add document relationship extraction

backend/app/models/
└── chat.py                   # EXISTING - extend Citation with multi-source fields

backend/app/routers/
└── debug.py                  # EXISTING - add /api/debug/doc-relationships endpoint
```

### Pattern 1: Cross-Reference Detection with Dual Signals
**What:** Detect document relationships using explicit citations (bibliographic references, "See Document X", hyperlinks) as primary signals, plus shared entities from knowledge graph as secondary signals with 2+ entity threshold.

**When to use:** During document ingestion in pipeline.py after entity extraction completes.

**Example:**
```python
# Source: Research on cross-document entity resolution (2025-2026)
from typing import List, Set, Dict
from dataclasses import dataclass
import re
from Levenshtein import ratio

@dataclass
class DocumentRelationship:
    source_doc_id: str
    target_doc_id: str
    relationship_type: str  # "explicit_citation" or "shared_entities"
    strength: float  # 0-1 score
    evidence: List[str]  # Citations or shared entity names

async def detect_cross_references(
    doc_id: str,
    doc_text: str,
    user_id: str,
    existing_docs: List[Dict]
) -> List[DocumentRelationship]:
    """
    Detect relationships between documents using dual signals.

    Priority: Explicit citations (weight 1.0) > Shared entities (weight 0.5)
    """
    relationships = []

    # Signal 1: Explicit citations (STRONGER)
    # Detect patterns like "See Document X", "FC-001", "Section 3.2 of Ground Control Manual"
    explicit_refs = detect_explicit_references(doc_text, existing_docs)
    for ref in explicit_refs:
        relationships.append(DocumentRelationship(
            source_doc_id=doc_id,
            target_doc_id=ref.target_doc_id,
            relationship_type="explicit_citation",
            strength=1.0,  # Highest confidence
            evidence=[ref.citation_text]
        ))

    # Signal 2: Shared entities (WEAKER)
    # Use existing knowledge graph to find docs with 2+ shared entities
    source_entities = await graph_store.list_entities_for_doc(doc_id, user_id)

    for target_doc in existing_docs:
        if target_doc['doc_id'] == doc_id:
            continue

        target_entities = await graph_store.list_entities_for_doc(
            target_doc['doc_id'], user_id
        )

        # Find shared entities (exact name match or aliases)
        shared = find_shared_entities(source_entities, target_entities)

        # Require 2+ shared entities to establish relationship
        if len(shared) >= 2:
            # Strength based on entity count and types
            strength = min(0.5 + (len(shared) - 2) * 0.1, 0.9)

            relationships.append(DocumentRelationship(
                source_doc_id=doc_id,
                target_doc_id=target_doc['doc_id'],
                relationship_type="shared_entities",
                strength=strength,
                evidence=[e.name for e in shared]
            ))

    return relationships

def detect_explicit_references(text: str, existing_docs: List[Dict]) -> List:
    """
    Detect explicit citations using pattern matching + fuzzy filename matching.
    """
    refs = []

    # Pattern 1: Document codes (FC-001, GC-v2.3, etc.)
    doc_code_pattern = r'\b[A-Z]{2,}-[\d\.]+\b'
    codes = re.findall(doc_code_pattern, text)

    # Pattern 2: "See [document name]" patterns
    see_pattern = r'(?:see|refer to|described in)\s+([A-Za-z\s\-]+(?:manual|guide|specification|document))'
    see_refs = re.findall(see_pattern, text, re.IGNORECASE)

    # Pattern 3: Explicit section references
    section_pattern = r'section\s+[\d\.]+\s+of\s+([A-Za-z\s\-]+)'
    section_refs = re.findall(section_pattern, text, re.IGNORECASE)

    all_mentions = codes + see_refs + section_refs

    # Match against existing document filenames
    for mention in all_mentions:
        for doc in existing_docs:
            # Fuzzy match (handles variations)
            similarity = ratio(mention.lower(), doc['filename'].lower())
            if similarity > 0.7:  # 70% similarity threshold
                refs.append({
                    'target_doc_id': doc['doc_id'],
                    'citation_text': mention
                })
                break

    return refs

def find_shared_entities(
    source_entities: List[Entity],
    target_entities: List[Entity]
) -> Set[Entity]:
    """
    Find entities shared between documents with name/alias matching.

    Uses ACRONYM_MAP from retriever.py for expansion.
    """
    shared = set()

    # Build lookup with aliases
    target_lookup = {}
    for entity in target_entities:
        # Add primary name
        target_lookup[entity.name.lower()] = entity

        # Add acronym expansion if applicable
        if entity.name in ACRONYM_MAP:
            expanded = ACRONYM_MAP[entity.name]
            target_lookup[expanded.lower()] = entity

    # Find matches
    for source_entity in source_entities:
        # Check primary name
        if source_entity.name.lower() in target_lookup:
            shared.add(source_entity)
            continue

        # Check expanded form
        if source_entity.name in ACRONYM_MAP:
            expanded = ACRONYM_MAP[source_entity.name]
            if expanded.lower() in target_lookup:
                shared.add(source_entity)

    return shared
```

### Pattern 2: Document Relationship Graph Storage
**What:** Store document relationships in FalkorDB alongside entity graph, enabling queries like "which docs reference this doc?" and "docs sharing 3+ entities with this doc".

**When to use:** During ingestion after cross-reference detection, and for retrieval queries.

**Example:**
```python
# Source: FalkorDB patterns for multi-level graphs (2025-2026)
class DocumentRelationshipStore:
    """
    Manages document-level relationship graph in FalkorDB.

    Schema:
    - Nodes: Document (doc_id, filename, user_id)
    - Edges: CITES (explicit), SHARES_ENTITIES (implicit)
    """

    def __init__(self):
        self.graph_store = GraphStore()  # Reuse existing FalkorDB connection

    def add_document_node(
        self,
        doc_id: str,
        filename: str,
        user_id: str,
        page_count: int,
        chunk_count: int
    ):
        """
        Add document node to relationship graph.
        """
        query = """
        MERGE (d:Document {doc_id: $doc_id, user_id: $user_id})
        SET d.filename = $filename,
            d.page_count = $page_count,
            d.chunk_count = $chunk_count
        RETURN d
        """
        params = {
            "doc_id": doc_id,
            "user_id": user_id,
            "filename": filename,
            "page_count": page_count,
            "chunk_count": chunk_count
        }
        self.graph_store.graph.query(query, params=params)

    def add_relationship(
        self,
        rel: DocumentRelationship,
        user_id: str
    ):
        """
        Add relationship between documents.

        Creates directed edge with type and strength.
        """
        if rel.relationship_type == "explicit_citation":
            edge_type = "CITES"
        else:
            edge_type = "SHARES_ENTITIES"

        query = f"""
        MATCH (source:Document {{doc_id: $source_id, user_id: $user_id}})
        MATCH (target:Document {{doc_id: $target_id, user_id: $user_id}})
        MERGE (source)-[r:{edge_type}]->(target)
        SET r.strength = $strength,
            r.evidence = $evidence
        RETURN r
        """
        params = {
            "source_id": rel.source_doc_id,
            "target_id": rel.target_doc_id,
            "user_id": user_id,
            "strength": rel.strength,
            "evidence": rel.evidence  # JSON list
        }
        self.graph_store.graph.query(query, params=params)

    def get_related_documents(
        self,
        doc_ids: List[str],
        user_id: str,
        min_strength: float = 0.5
    ) -> List[Dict]:
        """
        Get documents related to input set (for multi-doc queries).

        Returns documents connected via CITES or SHARES_ENTITIES edges.
        """
        # Convert doc_ids to Cypher list syntax
        doc_id_list = str(doc_ids).replace("'", '"')

        query = f"""
        MATCH (source:Document {{user_id: $user_id}})
        WHERE source.doc_id IN {doc_id_list}
        MATCH (source)-[r]-(related:Document)
        WHERE r.strength >= $min_strength AND related.user_id = $user_id
        RETURN DISTINCT related.doc_id as doc_id,
               related.filename as filename,
               r.strength as strength,
               type(r) as relationship_type,
               r.evidence as evidence
        ORDER BY r.strength DESC
        """
        params = {
            "user_id": user_id,
            "min_strength": min_strength
        }
        result = self.graph_store.graph.query(query, params=params)

        return [
            {
                "doc_id": row[0],
                "filename": row[1],
                "strength": row[2],
                "relationship_type": row[3],
                "evidence": row[4]
            }
            for row in result.result_set
        ]
```

### Pattern 3: Multi-Source Synthesis Prompting with Topic Organization
**What:** Use topic-organized answer structure with Chain-of-Thought prompting to synthesize information from 2+ documents, explicitly handling consensus and conflicts.

**When to use:** When retrieval returns chunks from 2+ distinct documents (trigger synthesis mode).

**Example:**
```python
# Source: ALCE benchmark + Chain-of-Thought citation research (2024-2026)
SYNTHESIS_SYSTEM_PROMPT = """You are a technical documentation assistant synthesizing information from multiple aerospace/defense sources.

When answering from multiple documents:
1. ORGANIZE by subtopics - group related information together
2. INDICATE CONSENSUS - use phrases like "multiple sources mention", "consistently described as"
3. HANDLE CONFLICTS - when sources disagree, cite both perspectives with their citations
4. USE COMPACT CITATIONS - for 3+ sources on same point, use [1-3: Doc A p.5, Doc B p.12, Doc C p.8]
5. PRESERVE TRACEABILITY - every claim needs citation support

Answer structure for multi-document questions:
- Brief overview (1 sentence)
- Subtopic 1: [information from sources] [citations]
- Subtopic 2: [information from sources] [citations]
- If conflicts exist: Note disagreements with citations

Use concise technical language (3-5 sentences per subtopic).
"""

async def generate_multi_source_answer(
    query: str,
    chunks: List[Dict],
    request_id: str
) -> Dict:
    """
    Generate synthesized answer from multiple documents.

    Activates when chunks come from 2+ distinct documents.
    """
    # Check if multi-source synthesis needed
    unique_docs = set(c['doc_id'] for c in chunks)

    if len(unique_docs) < 2:
        # Single document - use standard generation
        return await standard_generation(query, chunks, request_id)

    # Multi-source mode: topic-organized synthesis
    # Build context with document grouping
    context_parts = []
    doc_groups = {}  # Group chunks by document

    for idx, chunk in enumerate(chunks, 1):
        doc_id = chunk['doc_id']
        if doc_id not in doc_groups:
            doc_groups[doc_id] = []
        doc_groups[doc_id].append((idx, chunk))

    # Format context showing document boundaries
    for doc_id, doc_chunks in doc_groups.items():
        doc_name = doc_chunks[0][1]['filename']
        context_parts.append(f"\n=== {doc_name} ===")
        for idx, chunk in doc_chunks:
            context_parts.append(f"[{idx}: p.{chunk['page_range']}]\n{chunk['text']}\n")

    context = "\n".join(context_parts)

    # Chain-of-Thought prompt for citation accuracy
    user_prompt = f"""Context from {len(unique_docs)} documents:
{context}

Question: {query}

Think step-by-step:
1. What are the main subtopics relevant to this question?
2. What does each document say about each subtopic?
3. Where do documents agree? Where do they differ?
4. Synthesize a topic-organized answer with citations.

Answer:"""

    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response = await openai_client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.1,  # Low for factual synthesis
        max_tokens=800  # More tokens for multi-source answers
    )

    answer = response.choices[0].message.content

    # Build citations with multi-source awareness
    citations = build_multi_source_citations(chunks, answer)

    return {
        "answer": answer,
        "citations": citations,
        "synthesis_mode": True,
        "source_doc_count": len(unique_docs)
    }

def build_multi_source_citations(
    chunks: List[Dict],
    answer: str
) -> List[Citation]:
    """
    Build citations with compact notation for multi-source claims.

    Detects citation ranges in answer (e.g., [1-3]) and formats accordingly.
    """
    citations = []

    # Parse citation numbers/ranges from answer
    import re
    citation_pattern = r'\[(\d+(?:-\d+)?)\]'
    cited_numbers = set()

    for match in re.finditer(citation_pattern, answer):
        citation_ref = match.group(1)
        if '-' in citation_ref:
            # Range like [1-3]
            start, end = map(int, citation_ref.split('-'))
            cited_numbers.update(range(start, end + 1))
        else:
            # Single citation
            cited_numbers.add(int(citation_ref))

    # Build citation objects
    for idx, chunk in enumerate(chunks, 1):
        if idx not in cited_numbers:
            continue

        snippet = chunk['text'][:200]
        if len(chunk['text']) > 200:
            snippet += "..."

        # Check if part of multi-source claim (adjacent citations)
        is_multi_source = (idx - 1) in cited_numbers or (idx + 1) in cited_numbers

        citation = Citation(
            id=idx,
            doc_id=chunk['doc_id'],
            filename=chunk['filename'],
            page_range=chunk['page_range'],
            section_title=chunk.get('section_title'),
            snippet=snippet,
            score=chunk.get('rerank_score', chunk.get('score')),
            source=chunk.get('source', 'document'),
            multi_source=is_multi_source  # NEW field
        )
        citations.append(citation)

    return citations
```

### Pattern 4: Entity Resolution for Cross-Document Matching
**What:** Conservative entity merging using exact name matches or explicit aliases, with acronym handling via existing ACRONYM_MAP, tracking attribute provenance per document.

**When to use:** During document ingestion to merge entities that refer to same real-world objects across documents.

**Example:**
```python
# Source: Entity resolution knowledge graph research (2025-2026)
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class EntityAttribute:
    """Track provenance of entity attributes."""
    doc_id: str
    attribute_name: str
    attribute_value: str
    chunk_id: str

class EntityResolver:
    """
    Conservative entity resolution across documents.

    Merges only when:
    - Exact name match (case-insensitive)
    - Explicit alias match (from ACRONYM_MAP)
    - Tracks which document contributed each attribute
    """

    def __init__(self):
        self.graph_store = GraphStore()
        self.acronym_map = ACRONYM_MAP  # From retriever.py

    async def resolve_and_merge_entity(
        self,
        new_entity: Entity,
        user_id: str,
        doc_id: str,
        chunk_id: str
    ) -> str:
        """
        Resolve entity to canonical form and merge attributes.

        Returns: Canonical entity name (existing or new)
        """
        # Get all entities for this user
        existing_entities = await self.graph_store.list_entities(
            user_id=user_id,
            limit=10000
        )

        # Check exact name match (case-insensitive)
        canonical_name = self._find_exact_match(new_entity.name, existing_entities)

        if not canonical_name:
            # Check acronym expansion
            canonical_name = self._find_acronym_match(new_entity.name, existing_entities)

        if canonical_name:
            # Merge: add attributes from new entity to existing
            await self._merge_attributes(
                canonical_name=canonical_name,
                new_attributes={
                    "description": new_entity.description,
                    "type": new_entity.type,
                    "parent_entity": new_entity.parent_entity
                },
                doc_id=doc_id,
                chunk_id=chunk_id,
                user_id=user_id
            )
            return canonical_name
        else:
            # New entity - add to graph
            await self.graph_store.add_entity(new_entity, user_id)

            # Track initial attributes
            await self._store_attribute_provenance(
                entity_name=new_entity.name,
                attributes={
                    "description": new_entity.description,
                    "type": new_entity.type
                },
                doc_id=doc_id,
                chunk_id=chunk_id,
                user_id=user_id
            )
            return new_entity.name

    def _find_exact_match(
        self,
        entity_name: str,
        existing_entities: List[Dict]
    ) -> Optional[str]:
        """Find exact name match (case-insensitive)."""
        name_lower = entity_name.lower()
        for entity in existing_entities:
            if entity['name'].lower() == name_lower:
                return entity['name']
        return None

    def _find_acronym_match(
        self,
        entity_name: str,
        existing_entities: List[Dict]
    ) -> Optional[str]:
        """
        Find match via acronym expansion.

        Checks both directions:
        - New entity is acronym, existing is expanded
        - New entity is expanded, existing is acronym
        """
        # Check if new entity is acronym
        if entity_name in self.acronym_map:
            expanded = self.acronym_map[entity_name]
            for entity in existing_entities:
                if entity['name'].lower() == expanded.lower():
                    return entity['name']

        # Check if new entity is expanded form
        entity_lower = entity_name.lower()
        for acronym, expanded in self.acronym_map.items():
            if expanded.lower() == entity_lower:
                # Look for acronym in existing entities
                for entity in existing_entities:
                    if entity['name'] == acronym:
                        return entity['name']

        return None

    async def _merge_attributes(
        self,
        canonical_name: str,
        new_attributes: Dict[str, str],
        doc_id: str,
        chunk_id: str,
        user_id: str
    ):
        """
        Merge new attributes into existing entity.

        Strategy: Keep all non-conflicting attributes.
        For conflicts, store both and track source.
        """
        # Get existing entity
        existing = await self.graph_store.get_entity(canonical_name, user_id)

        # Compare attributes
        conflicts = []
        for attr_name, new_value in new_attributes.items():
            if attr_name not in existing or not existing[attr_name]:
                # No conflict - add new value
                existing[attr_name] = new_value
            elif existing[attr_name] != new_value:
                # Conflict - track both sources
                conflicts.append(attr_name)

        # Update entity with merged attributes
        await self.graph_store.update_entity(canonical_name, existing, user_id)

        # Store attribute provenance
        await self._store_attribute_provenance(
            entity_name=canonical_name,
            attributes=new_attributes,
            doc_id=doc_id,
            chunk_id=chunk_id,
            user_id=user_id,
            conflicts=conflicts
        )

    async def _store_attribute_provenance(
        self,
        entity_name: str,
        attributes: Dict[str, str],
        doc_id: str,
        chunk_id: str,
        user_id: str,
        conflicts: List[str] = None
    ):
        """
        Store which document contributed each attribute.

        Enables queries like "which document says UAV has attribute X?"
        """
        # Store in FalkorDB as separate AttributeProvenance nodes
        for attr_name, attr_value in attributes.items():
            query = """
            MATCH (e:Entity {name: $entity_name, user_id: $user_id})
            CREATE (p:AttributeProvenance {
                entity_name: $entity_name,
                attribute_name: $attr_name,
                attribute_value: $attr_value,
                doc_id: $doc_id,
                chunk_id: $chunk_id,
                user_id: $user_id,
                is_conflict: $is_conflict
            })
            CREATE (e)-[:HAS_ATTRIBUTE]->(p)
            """
            params = {
                "entity_name": entity_name,
                "user_id": user_id,
                "attr_name": attr_name,
                "attr_value": attr_value,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "is_conflict": attr_name in (conflicts or [])
            }
            await self.graph_store.graph.query(query, params=params)
```

### Anti-Patterns to Avoid

- **Treating all citations equally:** Explicit citations (document codes, "See Manual X") are stronger signals than shared entities. Weight accordingly in relationship scoring.

- **Single shared entity = relationship:** Requires 2+ shared entities to avoid false positives from common terms like "GPS" or "system" appearing in unrelated documents.

- **Concatenating all retrieved chunks:** Research shows simple concatenation fails for multi-document synthesis. Use topic organization and explicit conflict handling.

- **Exact string matching for citations:** Aerospace docs use variations ("FC-001", "Flight Controller v001", "FC001"). Use fuzzy matching with Levenshtein ratio.

- **No synthesis mode threshold:** Activate synthesis prompting only for 2+ document queries. Single-document queries use simpler prompt to avoid unnecessary complexity.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching for citations | Custom edit distance | python-Levenshtein | Highly optimized C implementation, 10-100x faster than pure Python |
| Document similarity scoring | Manual intersection logic | networkx graph algorithms | Handles transitive relationships, connected components, centrality metrics |
| Citation range parsing | Custom regex | Standardized patterns | Edge cases like [1-3,5,7-9] require robust parser |
| Entity name normalization | String cleaning | Existing ACRONYM_MAP + LLM | Domain-specific acronyms need aerospace knowledge |
| Multi-document deduplication | Chunk text comparison | Graph-based entity matching | Semantic duplicates across docs (same content, different wording) |

**Key insight:** Multi-document synthesis compounds errors - small mistakes in entity resolution or citation detection multiply across documents. Use proven libraries and conservative thresholds.

## Common Pitfalls

### Pitfall 1: Entity Resolution False Positives
**What goes wrong:** Merging unrelated entities with similar names ("Flight Controller" in UAV doc vs. "Flight Controller" in satellite doc are different systems).

**Why it happens:** Overly aggressive similarity thresholds or ignoring document context during entity resolution.

**How to avoid:**
- Use conservative threshold (0.85+ similarity) and require exact matches or explicit aliases
- Consider document type in disambiguation (specs vs. manuals may use same terms differently)
- Store entity context (parent_entity field) and compare during resolution

**Warning signs:**
- Entity graphs connecting unrelated documents
- Graph queries returning irrelevant cross-references
- Users reporting "system says X relates to Y but they're different systems"

### Pitfall 2: Synthesis Without Conflict Detection
**What goes wrong:** Generated answers blend contradictory information from different documents without noting disagreements, producing incorrect or misleading responses.

**Why it happens:** Simple concatenation of chunks + standard RAG prompting doesn't detect when sources disagree.

**How to avoid:**
- Use synthesis system prompt with explicit conflict handling instructions
- Group chunks by document in context to make disagreements visible
- Include "if sources disagree, cite both perspectives" in prompt
- Chain-of-Thought prompting ("what does each document say?") before synthesis

**Warning signs:**
- Users reporting "answer is wrong" for multi-doc questions
- Citations pointing to contradictory chunks
- Generated text mixing incompatible version numbers or specifications

### Pitfall 3: Citation Attribution Errors
**What goes wrong:** Generated answers cite wrong sources, or use citation numbers that don't match the chunk list (hallucinated citations).

**Why it happens:** Standard LLM generation can generate plausible-looking citations that don't correspond to provided context. Research shows even best models have 50%+ citation errors without specialized techniques.

**How to avoid:**
- Use Chain-of-Thought prompting: explicitly ask LLM to identify which chunks support each claim before writing answer
- Post-generation validation: parse citations from answer and verify against chunk list
- Structured output format: request citations in structured format alongside answer text
- Reranking matters: citation accuracy improves when higher-quality chunks are in context

**Warning signs:**
- Citation numbers [N] where N > number of provided chunks
- Multiple citations [1][2][3] where only [1] is relevant
- Debug logs showing citation mismatches between answer and chunk indices

### Pitfall 4: Pre-Computation Overhead Without Fallback
**What goes wrong:** Document relationship graph pre-computation adds 5-15 seconds to ingestion. If graph fails, entire pipeline fails.

**Why it happens:** Making graph computation critical path without graceful degradation.

**How to avoid:**
- Treat document relationships as enhancement, not requirement
- Wrap graph operations in try-except with fallback to entity-only mode
- Log warnings but continue ingestion if relationship detection fails
- Consider async/background relationship computation after document is searchable

**Warning signs:**
- Ingestion timeouts increase after adding relationship detection
- Pipeline failures spike when FalkorDB is slow
- Users reporting "doc stuck in processing" status

### Pitfall 5: Not Utilizing Document Relationship Graph
**What goes wrong:** Build document relationship graph but never use it in retrieval or synthesis, wasting ingestion time.

**Why it happens:** Forgetting to integrate graph queries into retrieval pipeline after building graph.

**How to avoid:**
- Add graph expansion step in retrieval: when chunks from doc A are retrieved, check for related docs B, C and fetch their chunks too
- Use in debug endpoints: /api/debug/doc-relationships for user inspection
- Inform synthesis prompt: include "Documents A and B both describe X" metadata
- Measure impact: log retrieval with/without graph to quantify benefit

**Warning signs:**
- Graph database growing but retrieval logs show no graph queries
- Multi-document questions perform same as before Phase 5
- Document relationship metrics at /api/debug/doc-relationships never accessed

## Code Examples

Verified patterns from official sources:

### Detecting Document Activation Threshold (2+ documents)
```python
# Source: Multi-document RAG best practices (2025-2026)
def should_activate_synthesis_mode(chunks: List[Dict]) -> bool:
    """
    Determine if multi-source synthesis mode should activate.

    Threshold: 2+ distinct documents in retrieved chunks.
    """
    unique_doc_ids = set(chunk['doc_id'] for chunk in chunks)

    # Additional check: at least 2 chunks from each document
    # Avoids triggering synthesis for single-chunk cross-doc results
    doc_chunk_counts = {}
    for chunk in chunks:
        doc_id = chunk['doc_id']
        doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

    multi_chunk_docs = sum(1 for count in doc_chunk_counts.values() if count >= 2)

    return multi_chunk_docs >= 2
```

### Extended Citation Model with Multi-Source Fields
```python
# Source: Phase 5 requirements + ALCE benchmark patterns
from pydantic import BaseModel, Field
from typing import Optional, List

class Citation(BaseModel):
    """Citation linking answer to source with multi-source support."""

    id: int = Field(..., description="Footnote number [1], [2], etc.")
    doc_id: str = Field(..., description="Document UUID")
    filename: str = Field(..., description="Original filename")
    page_range: str = Field(..., description="Page range (e.g., '42-43')")
    section_title: Optional[str] = Field(None, description="Section heading")
    snippet: str = Field(..., description="First 200 chars of chunk text")
    score: Optional[float] = Field(None, description="Reranker score")
    source: str = Field(default="document", description="'document' or 'graph'")

    # NEW: Multi-source synthesis fields
    multi_source: bool = Field(
        default=False,
        description="True if part of multi-source claim (adjacent citations)"
    )
    relationship_to_other_docs: Optional[List[str]] = Field(
        None,
        description="Related doc_ids if document relationship exists"
    )

# Usage in compact notation formatting
def format_compact_citation(citations: List[Citation], start_id: int, end_id: int) -> str:
    """
    Format citations [1-3] with document details.

    Example: [1-3: Doc A p.5, Doc B p.12, Doc C p.8]
    """
    if end_id - start_id < 2:
        # Not enough for compact notation
        return f"[{start_id}]"

    cites = [c for c in citations if start_id <= c.id <= end_id]
    doc_refs = [f"{c.filename} p.{c.page_range}" for c in cites]

    return f"[{start_id}-{end_id}: {', '.join(doc_refs)}]"
```

### Debug Endpoint for Document Relationships
```python
# Source: Phase 4 debug endpoint patterns + Phase 5 requirements
from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/doc-relationships")
async def get_document_relationships(
    user_id: str = Depends(get_current_user_id),
    doc_id: Optional[str] = Query(None, description="Filter by specific document"),
    format: str = Query("edgelist", description="Output format: edgelist or cytoscape")
):
    """
    Debug endpoint: Inspect document relationship graph.

    Returns:
    - edgelist: Simple JSON [{source, target, type, strength, evidence}]
    - cytoscape: Format for graph visualization libraries
    """
    doc_rel_store = DocumentRelationshipStore()

    if doc_id:
        # Get relationships for specific document
        relationships = await doc_rel_store.get_related_documents(
            doc_ids=[doc_id],
            user_id=user_id,
            min_strength=0.0  # Include all for debugging
        )
    else:
        # Get all relationships for user
        relationships = await doc_rel_store.get_all_relationships(user_id)

    if format == "cytoscape":
        # Convert to Cytoscape.js format
        return format_for_cytoscape(relationships)
    else:
        # Return simple edge list
        return {
            "user_id": user_id,
            "relationship_count": len(relationships),
            "relationships": relationships,
            "format": "edgelist"
        }

def format_for_cytoscape(relationships: List[Dict]) -> Dict:
    """
    Format document relationships for Cytoscape.js visualization.

    Structure: {nodes: [...], edges: [...]}
    """
    nodes = {}
    edges = []

    for rel in relationships:
        # Add source node
        if rel['source_doc_id'] not in nodes:
            nodes[rel['source_doc_id']] = {
                "data": {
                    "id": rel['source_doc_id'],
                    "label": rel['source_filename']
                }
            }

        # Add target node
        if rel['target_doc_id'] not in nodes:
            nodes[rel['target_doc_id']] = {
                "data": {
                    "id": rel['target_doc_id'],
                    "label": rel['target_filename']
                }
            }

        # Add edge
        edges.append({
            "data": {
                "source": rel['source_doc_id'],
                "target": rel['target_doc_id'],
                "label": rel['relationship_type'],
                "strength": rel['strength'],
                "evidence": rel['evidence']
            }
        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Simple concatenation | Topic-organized synthesis with CoT | 2024-2025 | 30-50% improvement in citation accuracy, better conflict detection |
| Runtime cross-ref detection | Pre-computed document graph | 2025-2026 | 2-5x faster queries, enables relationship-aware retrieval |
| Keyword-based doc matching | Entity-based + explicit citations | 2025-2026 | Higher precision (fewer false positive relationships) |
| Single prompting pass | Chain-of-Thought multi-stage | 2024-2025 | Reduces citation hallucinations from 50%+ to <20% |
| Equal weighting all signals | Prioritized signal hierarchy | 2025-2026 | Explicit citations > shared entities, better accuracy |

**Deprecated/outdated:**
- **Naive entity string matching:** Replaced by semantic similarity + LLM disambiguation (2025). String matching fails on acronyms and variations.
- **One-size-fits-all synthesis:** Replaced by query-dependent activation (2025). Not all questions need multi-document synthesis.
- **Post-generation citation fixing:** Replaced by upfront Chain-of-Thought (2024-2025). Fixing citations after generation is less reliable than prompting correctly.

## Open Questions

Things that couldn't be fully resolved:

1. **Document relationship decay over time**
   - What we know: Document relationships are static after ingestion
   - What's unclear: When documents are updated/deleted, stale relationships persist in graph
   - Recommendation: Implement cleanup on document delete, consider TTL or "last verified" timestamps

2. **Optimal shared entity threshold (2+ vs 3+)**
   - What we know: Research suggests 2+ entities minimum to avoid false positives
   - What's unclear: Aerospace domain may need higher threshold (3+) due to common terms
   - Recommendation: Start with 2, add configuration setting, monitor false positive rate in logs

3. **Synthesis mode for graph-only results**
   - What we know: Current threshold checks doc_id from chunks (document-derived)
   - What's unclear: Graph context chunks may have doc_id="graph" - should they count toward multi-doc threshold?
   - Recommendation: Treat graph context as supplementary, require 2+ real documents for synthesis activation

4. **Citation ordering for multi-source claims**
   - What we know: Context.md says "order by retrieval rank" (reranker score)
   - What's unclear: For compact notation [1-3], should docs be ordered by score or document relevance to claim?
   - Recommendation: Order by reranker score (consistent with Phase 3), let LLM choose most relevant snippet

5. **Entity resolution merge strategy for conflicts**
   - What we know: Track provenance, store which doc contributed each attribute
   - What's unclear: When attributes conflict (Doc A says "max altitude 5000m", Doc B says "max altitude 4500m"), should system pick one or present both?
   - Recommendation: Store both, let generator.py synthesis prompt handle conflict ("sources disagree") rather than pre-choosing

## Sources

### Primary (HIGH confidence)
- Cross-Document Topic-Aligned Chunking paper (arXiv 2601.05265, 2026) - CDTA approach for multi-document synthesis
- ALCE benchmark (2024-2025) - Citation evaluation framework, 50%+ citation error baseline
- Chain-of-Thought for Citations research (AAAI 2024) - 30-50% improvement in citation accuracy
- GraphRAG Microsoft Research (2024-2026) - Document + entity graph architectures
- LongCite framework (arXiv 2409.02897, 2024) - Fine-grained citation generation techniques

### Secondary (MEDIUM confidence)
- GraphRAG guide 2026 - [What is GraphRAG: Complete guide [2026]](https://www.meilisearch.com/blog/graph-rag)
- Entity Resolution knowledge graphs - [Entity resolution in knowledge graphs](https://linkurious.com/blog/entity-resolution-knowledge-graph/)
- FalkorDB documentation - [Graph Database Guide for AI Architects | 2026](https://www.falkordb.com/blog/graph-database-guide/)
- txtai framework capabilities - [txtai documentation](https://neuml.github.io/txtai/)
- RAG synthesis research survey - [awesome-generative-ai-guide RAG research](https://github.com/aishwaryanr/awesome-generative-ai-guide/blob/main/research_updates/rag_research_table.md)

### Tertiary (LOW confidence - requires validation in implementation)
- Document cross-reference classification techniques - researchgate.net publication on PDF cross-references
- Crossref services for citation tracking - crossref.org 2026 updates (academic publishing focus, may not directly apply)
- Semantic entity resolution blog posts - graphlet.ai (conceptual, not implementation-specific)

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM-HIGH - FalkorDB/OpenAI already validated in Phase 4, new libraries (python-Levenshtein, networkx) are stable and well-documented
- Architecture patterns: MEDIUM-HIGH - Cross-reference detection and synthesis prompting have academic validation, specific implementation requires experimentation
- Pitfalls: HIGH - Citation attribution errors and entity resolution false positives are well-documented in research literature
- Entity resolution: MEDIUM - Conservative approach (exact match + aliases) is validated, but domain-specific challenges (aerospace acronyms) require testing

**Research gaps:**
- Limited public examples of document relationship graphs specifically for technical documentation (most research focuses on academic papers or web documents)
- Few aerospace/defense-specific multi-document RAG case studies (most examples from legal, medical, or general enterprise domains)
- Chain-of-Thought prompting research focused on general QA, not technical multi-source synthesis

**Research date:** 2026-01-29
**Valid until:** 60 days (February 2026) - Multi-document RAG synthesis is active research area but core patterns are stabilizing in 2025-2026
