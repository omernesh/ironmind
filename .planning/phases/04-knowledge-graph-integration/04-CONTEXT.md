# Phase 4: Knowledge Graph Integration - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract entities (components, APIs, services, configurations, error modes) and their relationships from technical aerospace/defense documents to enable graph-aware retrieval. The graph enhances Phase 3's RAG pipeline by understanding how system components interconnect, enabling better answers for relationship-based and multi-component questions.

**Scope anchor:** Graph integration improves existing retrieval - it does NOT replace the hybrid RAG pipeline from Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Entity Granularity and Schema

- **Hierarchical extraction**: Extract both major components (systems, subsystems) AND their sub-components/details, with parent-child relationships linking them
- **Essential entity types** (all four required):
  - Hardware components: Physical systems, subsystems, modules, sensors, actuators
  - Software/services: APIs, services, protocols, interfaces, algorithms
  - Configuration parameters: Settings, thresholds, modes, flags
  - Error/failure modes: Error codes, fault conditions, failure scenarios
- **Abstract concepts included**: Extract conceptual entities like "redundancy", "failover", "autonomous navigation" to connect documents discussing similar concepts with different terminology
- **Acronym handling**: Expand acronyms to full forms (e.g., "UAV" → "Unmanned Aerial Vehicle") for better query matching
- **Action/verb entities**: Include action entities (e.g., "calibrate", "initialize", "transmit") to capture "what can be done" in addition to "what exists"
- **Ambiguity resolution**: Disambiguate entity references using surrounding context (e.g., distinguish "flight controller" from "ground controller" based on document context)
- **Singleton entities**: Include entities that appear only once - completeness matters, even rare entities might be important

### Relationship Extraction

- **Multi-document connections**: Use both approaches
  - Explicit cross-references when documents directly reference each other ("see Section 3.2 of Ground Control Manual")
  - Shared entity matching when documents mention the same entities but don't directly cross-reference
- **Result completeness**: Configurable via query phrasing
  - "All components that use X" → exhaustive list
  - "Key components that use X" → top-K most relevant

### Answer Enrichment

- **Explicitness level**: Configurable verbosity based on query complexity
  - Simple questions → concise answers with implicit graph context
  - Complex relationship questions → explicit graph information ("X depends on Y, which connects to Z")
- **Graph-derived insights**: Include graph inferences BUT clearly distinguish them from document facts
  - Example: "Documents state X depends on Y. This implies X is indirectly affected by changes to Z."
  - Mark inferred vs. stated information for transparency
- **Multi-hop expansion**: Query-dependent depth
  - Simple questions → 1-hop neighbors only
  - Complex relationship questions → expand deeper based on need
- **Citation format**: Unified citation format for all information (document-based and graph-derived) - consistency over distinction

### Graph Visibility and Debugging

- **Debug endpoint**: Query-specific subgraph
  - GET /api/debug/graph/sample accepts query parameter
  - Returns subgraph relevant to that query for debugging retrieval
- **User access**: Optional graph view for all users
  - Provide graph visualization in UI (Phase 6 scope)
  - Educational and builds trust in system capabilities
- **API format**: Both formats available via query parameter
  - ?format=edgelist → Simple JSON edge list [{from, to, relationship}]
  - ?format=cytoscape → Graph visualization library format (D3.js, vis.js, Cytoscape)
- **Quality metrics**: Admin-only metrics dashboard
  - Detailed extraction accuracy, entity coverage at /api/admin/graph/metrics
  - Users see results, not diagnostics

### Claude's Discretion

- **Relationship types**: Optimize for all relationship types equally (dependencies, configurations, multi-component interactions) - let graph capture everything and see what emerges
- **Query optimization**: Support both troubleshooting ("why is X failing?") and informational ("what does X do?") queries equally
- **Domain tuning**: Start domain-agnostic, allow for aerospace-specific tuning if research identifies value
- **Version tracking**: Evaluate whether temporal/versioning support ("what changed between v2.1 and v2.3?") adds value vs. complexity for POC
- **Procedural sequencing**: Evaluate whether extracting procedural relationships (step1 → step2 → step3) improves configuration query answers
- **Comparison support**: Determine during research if comparison patterns ("difference between X and Y") are valuable for aerospace docs
- **Document-type awareness**: Evaluate if varying extraction by document type (specs vs. manuals vs. reports) improves quality

</decisions>

<specifics>
## Specific Ideas

- **Transparency priority**: User emphasized marking inferred vs. stated information - defense industry needs clear traceability between document facts and system inferences
- **Comprehensive entity coverage**: Include actions, concepts, and singleton entities - completeness valued over noise reduction
- **User-facing graph visualization**: Not just a debug tool - graph view should be available to regular users for exploration and trust-building
- **Format flexibility**: Support both edge list and visualization formats recognizing different consumers (developers vs. UI rendering)

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 04-knowledge-graph-integration*
*Context gathered: 2026-01-29*
