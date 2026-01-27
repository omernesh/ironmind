# Feature Research

**Domain:** RAG systems with knowledge graphs and hybrid retrieval for technical document Q&A
**Researched:** 2026-01-27
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unprofessional.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Source Citations with Snippets** | RAG without citations is a "black box" - users cannot verify accuracy | MEDIUM | Must include document ID, filename, page range, and text snippet. Preserve metadata during chunking. |
| **Semantic Vector Search** | Basic RAG capability - users expect natural language queries to work | LOW | Baseline requirement. txtai provides this out-of-box with embedding models. |
| **Keyword/Exact Match Search (BM25)** | Technical docs contain IDs, codes, parameters that must match exactly | MEDIUM | Hybrid retrieval is table stakes for technical domains. txtai supports BM25 natively. |
| **Multi-Document Retrieval** | Answers must synthesize across multiple sources, not just single doc | MEDIUM | Requires proper document ID tracking in metadata and fusion across document boundaries. |
| **Document Structure Preservation** | Headers, sections, tables must be preserved for context | MEDIUM | Critical for Docling integration. Metadata must capture section hierarchy. |
| **Conversation History** | Follow-up questions reference previous context | MEDIUM | LobeChat provides this, backend must support conversation context in prompts. |
| **Upload Status Feedback** | Users need to know when documents are indexed and ready | LOW | Processing → Indexed → Failed states. Prevents "why isn't my document working?" confusion. |
| **Response Latency < 10s** | Industry standard for RAG Q&A - beyond 10s feels broken | MEDIUM | 5-8s target for POC scale. Requires efficient retrieval (< 2s) + LLM call (3-5s). |
| **Structured JSON Logging** | Engineering-grade systems require debuggability | LOW | Timestamp, level, service, request_id, user_id. Critical for POC evaluation by technical reviewers. |
| **Authentication/Access Control** | Documents may be sensitive - anonymous access is unprofessional | LOW | LobeChat Better Auth provides this. Backend must validate authenticated requests. |

### Differentiators (Competitive Advantage)

Features that set the product apart and align with "engineering-grade AI" expectations for assignment evaluation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Knowledge Graph Entity Relationships** | Answers questions spanning multiple components/systems that pure vector search misses | HIGH | "How does service X connect to config Y?" requires graph traversal. txtai 7.0+ supports graph search. **Assignment differentiator.** |
| **Hybrid Retrieval with Rank Fusion** | Combines semantic + keyword results intelligently, not just concatenation | MEDIUM | Reciprocal Rank Fusion (RRF) is 2026 standard. Significantly improves precision for technical queries with mixed semantic/exact needs. |
| **Reranking with Cross-Encoder** | 30-50% improvement in retrieval precision vs basic vector similarity | MEDIUM-HIGH | Two-stage retrieval: retrieve top 20-50 → rerank to top 5-8. ms-marco-MiniLM is standard baseline. **High ROI upgrade.** |
| **Explainable Retrieval Pipeline** | Shows retrieval scores, fusion results, and which retrieval method contributed each chunk | MEDIUM | Debugging endpoint or logs showing semantic score, BM25 score, fusion rank. Critical for "engineering-grade" evaluation criteria. |
| **Semantic Chunking Strategy** | Chunks respect document structure (section boundaries) vs arbitrary character splits | MEDIUM | 2026 best practice for technical docs. Docling extracts structure; chunker uses it. Reduces 60% of boundary errors. |
| **Multi-Hop Reasoning via Graph** | Synthesizes answers requiring multiple relationship traversals (A→B→C) | HIGH | "What services depend on component X?" Graph enables this where vector search fails. Optional for v1, strong for v2. |
| **Context Window Optimization** | Retrieves related chunks within same section/document to improve coherence | MEDIUM | If chunk 3 scores high, also pull chunks 2-4 from same section. Reduces fragmentation. |
| **Audit Trail for Compliance** | Cryptographic chain of custody for retrieval → generation → response | HIGH | Defense industry requirement. Logs showing: query → chunks retrieved → LLM prompt → response. Enables regulatory audit. |
| **Query Decomposition for Complex Questions** | Breaks multi-part questions into subquestions, answers each, then synthesizes | HIGH | "What is X and how does it relate to Y?" → two queries. Shows thinking process. Enterprise RAG 2026 trend. |
| **Document Metadata Filtering** | Search within specific doc types, dates, or sections | LOW-MEDIUM | "Search only configuration docs" or "exclude appendices". Enhances precision when user knows context. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems or scope creep for POC.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-Time Collaborative Editing** | "Multiple users should edit docs together" | Massive complexity, not core to RAG value. POC is 2-3 users asking questions, not editing. | Read-only document access. Users upload their own copies. |
| **Fine-Tuned Custom LLM** | "We should fine-tune for aerospace domain" | Timeline killer (5 days), expensive, GPT-4 is already excellent at technical text. Premature optimization. | Use GPT-4 as-is with well-engineered prompts and retrieval. Defer fine-tuning to post-POC. |
| **Multi-Tenant SaaS Infrastructure** | "What if many users sign up?" | POC scope is 2-3 users. Multi-tenancy adds DB complexity, isolation logic, billing. Overengineering. | Single deployment, basic user auth. Document isolation by user_id in txtai metadata. |
| **Advanced RBAC (Role-Based Access)** | "Users should have admin/viewer roles" | Scope creep. Assignment evaluates RAG quality, not auth system sophistication. | Email/password authentication only. All authenticated users have same permissions. |
| **Streaming LLM Responses** | "Answers should appear word-by-word" | Adds complexity to backend (SSE/WebSocket), LobeChat integration, and citation rendering. Marginal UX gain for 5-8s responses. | Batch response with loading indicator. Simpler, more reliable for POC. |
| **Document Versioning** | "Track changes to uploaded docs" | Complicates indexing (which version to search?), storage, and UI. Not requested in assignment. | Single version per document. Re-upload replaces existing. |
| **Automatic Entity Extraction via Custom NER** | "Build custom Named Entity Recognition for aerospace" | Deep learning complexity, training data requirements, timeline risk. txtai's LLM-driven extraction is sufficient. | Use txtai's LLM-driven entity extraction (example 57) or simple rule-based extraction for v1. |
| **Multi-Modal RAG (Images, Diagrams)** | "Technical docs have diagrams" | Significant complexity (OCR, vision models, multimodal embeddings). High risk for 5-day timeline. | Text-only for POC. Docling extracts text; images ignored or placeholder text. Defer to v2 if needed. |
| **Real-Time Document Monitoring** | "Auto-reindex when docs change" | Requires file watching, incremental indexing, cache invalidation. Unnecessary for static upload-once workflow. | Manual upload only. User re-uploads if doc changes. |
| **Query Auto-Completion** | "Suggest questions as user types" | Requires query corpus analysis, UI integration. Low value vs effort for POC with technical users. | Standard text input. Provide example queries in UI/docs instead. |

## Feature Dependencies

```
[Hybrid Retrieval]
    ├──requires──> [Semantic Vector Search]      (baseline)
    ├──requires──> [BM25 Keyword Search]          (parallel)
    └──requires──> [Rank Fusion Algorithm]        (merge results)

[Knowledge Graph Retrieval]
    ├──requires──> [Entity Extraction]             (build graph)
    ├──requires──> [Relation Extraction]           (link entities)
    └──enhances──> [Multi-Document Synthesis]      (cross-doc relationships)

[Source Citations]
    ├──requires──> [Metadata Preservation]         (during chunking)
    └──requires──> [Chunk-to-Source Mapping]       (track provenance)

[Reranking]
    ├──requires──> [Hybrid Retrieval]              (provides candidate set)
    └──enhances──> [Source Citations]              (improves precision)

[Explainable Pipeline]
    ├──requires──> [Structured Logging]            (capture events)
    └──enhances──> [Debugging/Validation]          (visibility)

[Semantic Chunking]
    ├──requires──> [Document Structure Extraction] (Docling)
    └──enhances──> [Context Window Optimization]   (boundary-aware)

[Query Decomposition]
    ├──requires──> [Multi-Document Retrieval]      (subqueries)
    └──conflicts──> [Simple RAG Pipeline]          (architectural complexity)
```

### Dependency Notes

- **Hybrid Retrieval requires Rank Fusion:** BM25 and vector search produce incompatible scores. Reciprocal Rank Fusion (RRF) is standard fusion method.
- **Knowledge Graph enhances Multi-Document Synthesis:** Graph relationships connect entities across documents, enabling "service X uses config Y from different doc" queries.
- **Reranking requires Hybrid Retrieval first:** Rerankers (cross-encoders) are computationally expensive. Apply only to top 20-50 candidates from hybrid retrieval.
- **Semantic Chunking enhances Context Optimization:** Structure-aware chunks enable "retrieve adjacent chunks in same section" logic.
- **Query Decomposition conflicts with Simple Pipeline:** Adds LLM call for decomposition + multiple retrievals + synthesis. Deferred complexity for POC.

## MVP Definition

### Launch With (v1 - POC Deadline Feb 1)

Minimum viable product for assignment submission.

- [x] **Semantic Vector Search** — Baseline RAG capability
- [x] **BM25 Keyword Search** — Technical doc requirement (exact match on IDs/codes)
- [x] **Hybrid Retrieval with RRF** — Industry standard 2026, high value
- [x] **Source Citations (doc, page, snippet)** — Non-negotiable for explainability
- [x] **Document Structure Preservation** — Docling integration, section metadata
- [x] **Multi-Document Retrieval** — Assignment requires synthesis across docs
- [x] **Basic Knowledge Graph** — Entity/relation extraction, store in txtai graph
- [x] **Graph-Aware Retrieval** — Query graph for entity relationships
- [x] **Conversation History** — LobeChat provides, backend supports context
- [x] **Structured Logging** — Engineering-grade requirement (request_id, user_id, events)
- [x] **Authentication** — Basic email/password via LobeChat Better Auth
- [x] **Upload Status UI** — Processing/Indexed/Failed states
- [x] **Semantic Chunking** — Structure-aware splits (section boundaries)

**Rationale:** These features directly address assignment evaluation criteria: accuracy (hybrid + graph), multi-source synthesis (multi-doc + graph), explainability (citations + logging), and "engineering-grade AI" (structured approach, not ChatGPT wrapper).

### Add After Validation (v1.x - Post-Submission)

Features to add if POC is well-received and moves to pilot phase.

- [ ] **Reranking with Cross-Encoder** — 30-50% precision boost, worth complexity after baseline works
- [ ] **Explainable Retrieval Debug Endpoint** — Shows scores, fusion results, retrieval method contribution
- [ ] **Context Window Optimization** — Retrieve adjacent chunks from same section
- [ ] **Document Metadata Filtering** — "Search only service configs" or "exclude appendices"
- [ ] **Query Performance Metrics** — Latency breakdown (retrieval, LLM, total)
- [ ] **Chunk Overlap Strategy** — Overlap adjacent chunks to prevent information loss at boundaries

**Trigger for adding:** Positive feedback from IAI reviewers, request for pilot deployment, or specific feature requests.

### Future Consideration (v2+ - Production Path)

Features to defer until product-market fit is established or larger deployment.

- [ ] **Multi-Hop Reasoning via Graph** — Complex graph traversals (A→B→C reasoning)
- [ ] **Query Decomposition** — Break complex questions into subquestions
- [ ] **Audit Trail for Compliance** — Cryptographic chain of custody for defense compliance
- [ ] **Multi-Modal RAG** — Images, diagrams, tables as visual elements
- [ ] **Streaming LLM Responses** — Word-by-word generation (SSE/WebSocket)
- [ ] **Advanced RBAC** — Role-based permissions beyond basic auth
- [ ] **Document Versioning** — Track changes, search specific versions
- [ ] **Incremental Indexing** — Update index without full re-index
- [ ] **Query Auto-Completion** — Suggest questions based on corpus

**Why defer:** These features are either high complexity (multi-hop graph, audit trail), marginal value for POC (streaming, auto-complete), or premature for scale (RBAC, versioning). Focus v1 on core RAG excellence.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Notes |
|---------|------------|---------------------|----------|-------|
| Semantic Vector Search | HIGH | LOW | P1 | Baseline requirement, txtai built-in |
| BM25 Keyword Search | HIGH | LOW | P1 | txtai built-in, critical for technical docs |
| Hybrid Retrieval + RRF | HIGH | MEDIUM | P1 | Industry standard, required for accuracy |
| Source Citations | HIGH | MEDIUM | P1 | Non-negotiable for explainability |
| Multi-Document Retrieval | HIGH | LOW | P1 | Metadata tracking during chunking |
| Basic Knowledge Graph | HIGH | HIGH | P1 | Assignment differentiator, txtai 7.0 support |
| Graph-Aware Retrieval | HIGH | HIGH | P1 | Enables multi-component questions |
| Semantic Chunking | MEDIUM | MEDIUM | P1 | 60% error reduction for technical docs |
| Structured Logging | HIGH | LOW | P1 | Engineering-grade requirement |
| Reranking Cross-Encoder | HIGH | MEDIUM | P2 | 30-50% precision boost, add after v1 works |
| Explainable Debug Endpoint | MEDIUM | MEDIUM | P2 | Debugging aid, not user-facing |
| Context Window Optimization | MEDIUM | MEDIUM | P2 | Reduces fragmentation, nice-to-have |
| Document Metadata Filtering | MEDIUM | LOW | P2 | Power-user feature, defer to v1.x |
| Multi-Hop Graph Reasoning | HIGH | HIGH | P3 | Complex, defer to v2 |
| Query Decomposition | MEDIUM | HIGH | P3 | Architectural complexity, defer |
| Audit Trail (Compliance) | LOW* | HIGH | P3 | *LOW for POC, HIGH for defense production |
| Multi-Modal RAG | MEDIUM | HIGH | P3 | Timeline risk, defer to v2 |
| Streaming Responses | LOW | MEDIUM | P3 | Marginal UX gain for 5-8s responses |

**Priority key:**
- P1: Must have for POC launch (Feb 1 deadline)
- P2: Should have post-launch, high ROI
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | GraphRAG (Microsoft) | LangChain RAG | txtai RAG | Our Approach (DocRAG POC) |
|---------|---------------------|---------------|-----------|---------------------------|
| **Hybrid Retrieval** | ✓ (Azure Cognitive Search) | ✓ (via integrations) | ✓ (native BM25 + vectors) | ✓ Native txtai, RRF fusion |
| **Knowledge Graph** | ✓ (core feature, expensive) | ✓ (via Neo4j/etc) | ✓ (built-in semantic graph) | ✓ txtai graph, entity extraction |
| **Reranking** | ✓ (Azure rerank API) | ✓ (cross-encoder plugins) | ✗ (manual integration) | P2 (ms-marco-MiniLM post-v1) |
| **Source Citations** | ✓ (with Azure setup) | ✓ (via metadata) | ✓ (metadata tracking) | ✓ Chunk metadata → citations |
| **Multi-Hop Reasoning** | ✓ (graph traversal) | ✗ (requires custom) | Partial (graph search) | P3 (defer to v2) |
| **Query Decomposition** | ✓ (agent-based) | ✓ (LLM chains) | ✗ (manual) | P3 (defer, complexity) |
| **Complexity** | HIGH (enterprise) | HIGH (many integrations) | LOW (all-in-one) | MEDIUM (lightweight + graph) |
| **Cost** | $$$$ (Azure APIs) | Variable | Free (OSS) | $ (OpenAI GPT-4 only) |
| **Deployment** | Azure-locked | Self-hosted possible | Self-hosted | ✓ Docker, VPS/cloud |

**Our Differentiation:**
- Lightweight hybrid + graph without enterprise complexity (vs GraphRAG)
- Integrated stack without integration sprawl (vs LangChain)
- Engineering-grade explainability and logging (vs generic RAG)
- Optimized for technical document Q&A with aerospace/defense focus

## Sources

**Knowledge Graph RAG:**
- [RAG Tutorial: Knowledge Graph](https://neo4j.com/blog/developer/rag-tutorial/)
- [GraphRAG & Knowledge Graphs 2026](https://flur.ee/fluree-blog/graphrag-knowledge-graphs-making-your-data-ai-ready-for-2026/)
- [Next Frontier of RAG 2026-2030](https://nstarxinc.com/blog/the-next-frontier-of-rag-how-enterprise-knowledge-systems-will-evolve-2026-2030/)
- [Knowledge Graphs for RAG - DeepLearning.AI](https://www.deeplearning.ai/short-courses/knowledge-graphs-rag/)
- [Building KG RAG on Databricks](https://www.databricks.com/blog/building-improving-and-deploying-knowledge-graph-rag-systems-databricks)

**Hybrid Retrieval:**
- [Understanding Hybrid Search RAG](https://www.meilisearch.com/blog/hybrid-search-rag)
- [Azure AI Search RAG](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)
- [Optimizing RAG with Hybrid Search & Reranking](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking)
- [Hybrid Search Explained - Redis](https://redis.io/blog/hybrid-search-explained/)

**Technical Document Requirements:**
- [RAG at Scale 2026](https://redis.io/blog/rag-at-scale/)
- [Requirements Engineering for RAG Systems](https://arxiv.org/html/2505.07553v1)
- [Observations on Building RAG for Technical Docs](https://arxiv.org/abs/2404.00657)
- [RAG Evaluation Survey](https://arxiv.org/html/2504.14891v1)

**Citations & Traceability:**
- [FINOS - Citations & Source Traceability](https://air-governance-framework.finos.org/mitigations/mi-13_providing-citations-and-source-traceability-for-ai-generated-information.html)
- [Citation-Aware RAG](https://www.tensorlake.ai/blog/rag-citations)
- [Building Trustworthy RAG with Citations](https://haruiz.github.io/blog/improve-rag-systems-reliability-with-citations)
- [Effective Source Tracking in RAG](https://www.chitika.com/source-tracking-rag/)

**Multi-Document Synthesis:**
- [Next Frontier of RAG 2026-2030](https://nstarxinc.com/blog/the-next-frontier-of-rag-how-enterprise-knowledge-systems-will-evolve-2026-2030/)
- [Systematic Review of RAG Systems](https://arxiv.org/html/2507.18910v1)
- [Multimodal RAG Best Practices](https://www.augmentcode.com/guides/multimodal-rag-development-12-best-practices-for-production-systems)

**Explainability & Transparency:**
- [Ethical Imperatives for RAG](https://medinform.jmir.org/2026/1/e79922/PDF)
- [Importance of Explainability in Enterprise RAG](https://www.vectara.com/blog/the-importance-of-explainability-in-enterprise-rag)
- [RAG Models 2026 Strategic Guide](https://www.techment.com/blogs/rag-models-2026-enterprise-ai/)

**txtai Capabilities:**
- [txtai Semantic Graphs](https://github.com/neuml/txtai/blob/master/examples/38_Introducing_the_Semantic_Graph.ipynb)
- [Build Knowledge Graphs with LLM Entity Extraction](https://github.com/neuml/txtai/blob/master/examples/57_Build_knowledge_graphs_with_LLM_driven_entity_extraction.ipynb)
- [txtai v7.0 Release - Graph Search](https://github.com/neuml/txtai/releases/tag/v7.0.0)

**Chunking Strategies:**
- [Chunking Strategies for RAG](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Ultimate Guide to Chunking - Databricks](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089)
- [Azure RAG Chunking Phase](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-chunking-phase)
- [Semantic Boundaries Cut RAG Errors 60%](https://ragaboutit.com/the-chunking-strategy-shift-why-semantic-boundaries-cut-your-rag-errors-by-60/)

**Reranking:**
- [Rerankers and Two-Stage Retrieval](https://www.pinecone.io/learn/series/rag/rerankers/)
- [RAG in 2026 Practical Blueprint](https://dev.to/suraj_khaitan_f893c243958/-rag-in-2026-a-practical-blueprint-for-retrieval-augmented-generation-16pp)
- [Cross-Encoders in Re-Ranking](https://www.cloudthat.com/resources/blog/the-power-of-cross-encoders-in-re-ranking-for-nlp-and-rag-systems)
- [Adaptive Retrieval Reranking](https://ragaboutit.com/adaptive-retrieval-reranking-how-to-implement-cross-encoder-models-to-fix-enterprise-rag-ranking-failures/)

---
*Feature research for: DocRAG POC - RAG with Knowledge Graphs and Hybrid Retrieval*
*Researched: 2026-01-27*
*Confidence: MEDIUM-HIGH (verified with Context7, official docs, and 2026-dated sources)*
