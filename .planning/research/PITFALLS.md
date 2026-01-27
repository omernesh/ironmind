# Pitfalls Research

**Domain:** RAG + Knowledge Graph + Hybrid Retrieval for Technical Documents (Defense/Aerospace)
**Researched:** 2026-01-27
**Confidence:** MEDIUM-HIGH

## Critical Pitfalls

### Pitfall 1: Context Fragmentation Through Poor Chunking Strategy

**What goes wrong:**
Technical documents are hierarchical with meaning distributed across sections, tables, figures, and captions. Fixed-size chunking splits sentences mid-word, separates tables from their context, and disconnects figure references from explanations. Retrieved chunks lack structural context, causing the LLM to answer with incomplete or incorrect information.

**Why it happens:**
Developers default to simple character-based chunking (e.g., 512 tokens) because it's fast to implement. They underestimate how technical documents rely on structural relationships - a specification table means nothing without its preceding context paragraph.

**How to avoid:**
- Use semantic chunking that respects document structure (sections, subsections, tables)
- Preserve metadata: section headers, document title, page numbers, figure/table captions
- Keep related elements together: table + caption + context paragraph as single chunk
- For Docling integration: leverage its native section detection and table extraction
- Test chunking quality: manually inspect 20-30 chunks before full processing

**Warning signs:**
- Answers reference "the table" but don't specify which one
- System retrieves specifications without context (units, conditions, constraints)
- Cross-references break ("as shown in Figure 3" retrieved without Figure 3)
- Multi-step procedures get fragmented across chunks

**Phase to address:**
Phase 1 (Document Processing Setup) - Get chunking right before building retrieval layer

**Sources:**
- [Why Your RAG System Fails on Technical Documents (And How to Fix It)](https://medium.com/@officialchiragp1605/why-your-rag-system-fails-on-technical-documents-and-how-to-fix-it-5c9e5be7948f)
- [RAG Chunking Strategies: Complete Guide](https://latenode.com/blog/ai-frameworks-technical-infrastructure/rag-retrieval-augmented-generation/rag-chunking-strategies-complete-guide-to-document-splitting-for-better-retrieval)
- [Document Chunking for RAG: 9 Strategies Tested (70% Accuracy Boost)](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide)

---

### Pitfall 2: Inadequate Source Attribution and Traceability

**What goes wrong:**
System generates answers without explicit citations to source documents, page numbers, or section references. In defense/aerospace contexts, this makes answers unusable - engineers need to verify claims in original specs. Without provenance tracking, answers can't be audited or trusted.

**Why it happens:**
Basic RAG implementations focus on answer quality, treating source attribution as an afterthought. Metadata gets stripped during embedding or isn't propagated through the retrieval-generation pipeline. Knowledge graph edges lose their document source pointers.

**How to avoid:**
- Store rich metadata with every chunk: `{doc_id, doc_title, section, page, chunk_index}`
- Implement txtai's provenance tracking: keep source IDs and spans with each node
- Format LLM responses with inline citations: "According to [Doc A, p.12, Section 3.2]..."
- For multi-source answers: explicitly list all contributing documents
- Add citation coverage metric to evaluation: % of claims with verifiable sources

**Warning signs:**
- QA interface shows answers without "Source:" section
- User asks "where did this come from?" and you can't answer
- Evaluation reveals correct answers but wrong source documents cited
- Cannot reconstruct retrieval path from question → chunks → answer

**Phase to address:**
Phase 2 (Core RAG Pipeline) - Build attribution into retrieval architecture from start

**Sources:**
- [Effective Source Tracking in RAG Systems](https://www.chitika.com/source-tracking-rag/)
- [DocIndex: Retrieval-Augmented Generation with Source Traceability](https://keviinkibe.medium.com/docindex-retrieval-augmented-generation-with-source-traceability-fddc3b7441f5)
- [5 Key Features and Benefits of RAG (Microsoft Cloud Blog)](https://www.microsoft.com/en-us/microsoft-cloud/blog/2025/02/13/5-key-features-and-benefits-of-retrieval-augmented-generation-rag/)

---

### Pitfall 3: Hybrid Retrieval Tuning Without Baseline Measurements

**What goes wrong:**
Team implements BM25 + semantic search hybrid retrieval with arbitrary weights (e.g., 0.5/0.5) without measuring individual component performance. Wrong balance causes system to miss critical exact matches (part numbers, specifications) or fail on conceptual queries. Normalization issues cause one retriever to dominate.

**Why it happens:**
Hybrid retrieval is marketed as "best of both worlds" - developers assume combining methods automatically improves results. They skip the tedious work of evaluating BM25-only vs semantic-only vs hybrid on representative queries.

**How to avoid:**
- Establish baselines FIRST: test BM25-only, semantic-only on 30-50 representative queries
- Measure precision@k and recall@k for each retriever independently
- Use Reciprocal Rank Fusion (RRF) initially - works well out-of-box without tuning
- If using weighted combination: normalize scores (min-max scaling) and test multiple weights
- Create query type classification: exact-match vs conceptual vs hybrid-needed
- For technical docs: BM25 often performs better on specifications, part numbers, exact terminology

**Warning signs:**
- Retrieval returns semantically similar but factually wrong documents
- Exact part numbers or model numbers fail to retrieve correct specs
- One retriever dominates (check score distributions)
- Performance worse than BM25-only baseline

**Phase to address:**
Phase 3 (Hybrid Retrieval Integration) - After basic RAG works, before optimization

**Sources:**
- [Understanding Hybrid Search RAG for Better AI Answers](https://www.meilisearch.com/blog/hybrid-search-rag)
- [Hybrid Search: Combining BM25 and Semantic Search](https://lancedb.com/blog/hybrid-search-combining-bm25-and-semantic-search-for-better-results-with-lan-1358038fe7e6/)
- [Building Effective Hybrid Search in OpenSearch](https://opensearch.org/blog/building-effective-hybrid-search-in-opensearch-techniques-and-best-practices/)

---

### Pitfall 4: Knowledge Graph Extraction Without Quality Validation

**What goes wrong:**
LLM-based entity extraction produces noisy knowledge graphs: duplicate entities ("F-16", "F16", "Falcon"), wrong relationships, hallucinated connections. Graph structure looks impressive but contains 30-40% incorrect edges. Queries traverse wrong paths, producing confident but incorrect answers.

**Why it happens:**
Knowledge graph extraction seems magical - feed documents to LLM, get structured graph. Teams don't budget time for entity resolution, disambiguation, or relationship validation. No ground truth to compare against.

**How to avoid:**
- Start small: extract entities from 2-3 documents, manually verify before scaling
- Implement entity resolution: canonical forms for common entities (aircraft models, systems, components)
- Use knowledge graph validation prompts: "Are these relationships correct? [list edges]"
- Track extraction confidence scores per entity/relationship
- Build evaluation set: 50-100 verified entity-relationship triples for regression testing
- For txtai: leverage structured entity extraction with constrained vocabularies where possible

**Warning signs:**
- Graph visualization shows duplicate/near-duplicate nodes
- Same query returns different answers on repeated runs
- Entity counts seem too high (likely duplicates)
- Relationships contradict source documents when spot-checked

**Phase to address:**
Phase 4 (Knowledge Graph Integration) - Validate extraction quality before depending on graph

**Sources:**
- [Diagnosing and Addressing Pitfalls in KG-RAG](https://openreview.net/pdf?id=Vd5JXiX073)
- [Knowledge Graphs for Enhancing LLMs in Entity Disambiguation](https://arxiv.org/html/2505.02737v2)
- [Understanding Effect of KG Extraction Error on Downstream Analyses](https://link.springer.com/article/10.1007/s41109-025-00749-0)

---

### Pitfall 5: Docling Document Processing Failures Handled Silently

**What goes wrong:**
Docling hangs indefinitely on complex PDFs or fails silently on scanned documents, returning partial/empty results. Team doesn't notice until production evaluation reveals missing content from critical documents. Complex tables with merged cells produce garbled output that looks reasonable but contains wrong values.

**Why it happens:**
POC environments test on clean, simple PDFs. Real aerospace/defense documents have scanned pages, hand-annotated diagrams, complex nested tables, non-standard formatting. Docling's EasyOCR struggles with technical drawings and low-quality scans.

**How to avoid:**
- Test Docling on representative documents EARLY (day 1): scanned pages, complex tables, annotations
- Implement timeouts and fallbacks: `converter.timeout = 120s`, retry with simplified settings
- Validate extraction quality: check page counts, table cell counts, OCR confidence scores
- For complex tables: manually verify 10-20 extracted tables against originals
- Monitor resource usage: memory leaks common with AI-based OCR
- Have fallback strategy: alternative parser (Unstructured.io, LlamaParse) for problematic docs

**Warning signs:**
- Processing hangs without timeout
- Extracted text length much shorter than expected
- Table data has repeated values or obviously wrong numbers
- OCR confidence scores < 0.7 on critical documents

**Phase to address:**
Phase 1 (Document Processing Setup) - Validate Docling reliability on real documents immediately

**Sources:**
- [PDF Table Extraction Showdown: Docling vs. LlamaParse vs. Unstructured](https://boringbot.substack.com/p/pdf-table-extraction-showdown-docling)
- [Docling vs. LLMWhisperer: Best Docling Alternative in 2026](https://unstract.com/blog/docling-alternative/)
- [PDF Data Extraction Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)

---

### Pitfall 6: Multi-Document Synthesis Without Cross-Reference Detection

**What goes wrong:**
System retrieves relevant chunks from multiple documents but fails to detect when Document A references Document B's specifications. Answers miss critical cross-document dependencies (e.g., "System X requirements defined in Doc A depend on Interface Protocol in Doc B"). Users get incomplete answers that seem correct but violate inter-document constraints.

**Why it happens:**
Basic RAG treats documents as independent sources. No mechanism to detect explicit references (citations, "see Document Y") or implicit relationships (shared entities, related specifications). Retrieval returns top-k chunks without considering document relationships.

**How to avoid:**
- Extract cross-references during document processing: citation analysis, hyperlink mapping
- Build document relationship graph: which documents reference which
- Implement cross-document retrieval: when Doc A retrieved, check for referenced documents
- Use knowledge graph for entity linking: same component mentioned in multiple documents
- Add relationship metadata to chunks: `{references: ['Doc B Section 3'], related_entities: ['System X']}`
- Query expansion: "System X" query should retrieve from all documents mentioning System X

**Warning signs:**
- Answers cite specifications without mentioning dependent requirements from other docs
- User feedback: "Your answer contradicts the interface specification"
- Evaluation reveals correct per-document answers but wrong cross-document conclusions
- Missing critical constraints that span documents

**Phase to address:**
Phase 5 (Multi-Source Synthesis) - After basic retrieval works, before claiming multi-doc capability

**Sources:**
- [How to Build Contextual RAG Systems with Google's NotebookLM](https://ragaboutit.com/how-to-build-contextual-rag-systems-with-googles-notebooklm-the-complete-enterprise-knowledge-synthesis-guide/)
- [How to Build Production-Ready RAG with LangChain's Multi-Document Framework](https://ragaboutit.com/how-to-build-a-production-ready-rag-system-with-langchains-new-multi-document-processing-framework/)

---

### Pitfall 7: 5-Day Timeline Pressure Leading to Architectural Shortcuts

**What goes wrong:**
POC conflates offline indexing and online queries into monolithic script. Evaluation framework skipped or minimal (manual spot checks). No caching layer, every query hits LLM API. Works for demo but architecture doesn't scale or support iteration. Post-POC refactoring takes 2-3 weeks.

**Why it happens:**
5-day deadline forces "just make it work" mentality. Team prioritizes visible features (UI, sample answers) over infrastructure (proper pipeline separation, evaluation harness, caching). No time allocated for architectural planning.

**How to avoid:**
- Day 1: Architecture sketch - separate ingestion pipeline from query pipeline
- Implement semantic caching from start (txtai supports this) - saves LLM costs and latency
- Build evaluation harness EARLY (Day 2): 30-50 Q&A pairs with expected sources
- Use modular design: document processing → indexing → retrieval → generation as separate stages
- Avoid monolithic notebooks - structure as importable modules for testing
- Timebox features: if knowledge graph extraction takes > 1 day, defer to post-POC

**Warning signs:**
- Single script > 500 lines doing everything
- Can't test retrieval without running entire pipeline
- No automated evaluation - only manual demo queries
- Indexing re-runs on every query (no persistence)
- LLM API costs surprisingly high during development

**Phase to address:**
Phase 0 (Planning) & Phase 1 (Foundation) - Set architecture constraints before coding

**Sources:**
- [RAG at Scale: How to Build Production AI Systems in 2026](https://redis.io/blog/rag-at-scale/)
- [Scaling RAG from POC to Production](https://medium.com/data-science/scaling-rag-from-poc-to-production-31bd45d195c8)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Fixed-size chunking (512 tokens) | Fastest to implement, works in demos | Context fragmentation, poor answers on technical docs | Never for technical documents - always use semantic/structural chunking |
| No source attribution metadata | Simpler indexing pipeline | Unusable in production, can't verify answers | Never for defense/aerospace - regulatory requirement |
| Arbitrary hybrid weights (0.5/0.5) | Avoids tuning time | Suboptimal retrieval, may underperform single method | Acceptable for initial POC if RRF unavailable, must tune before eval |
| Skip entity resolution in KG | Faster extraction, graph looks bigger | 30-40% wrong relationships, unreliable answers | Acceptable only if not using KG for retrieval (visualization only) |
| Monolithic ingestion script | Faster development, one file to understand | Can't iterate/test components separately, hard to debug | Acceptable for POC if < 300 lines and modularized before Phase 6 |
| Manual evaluation only (no metrics) | No harness to build, saves 4-6 hours | Can't detect regressions, no evidence of quality | Never - build minimal eval harness (30 Q&A pairs) on Day 2 |

## Integration Gotchas

Common mistakes when connecting system components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| txtai + Docling | Feeding Docling's raw Markdown directly to txtai without preserving structure metadata | Extract Docling's section hierarchy, tables, figures as metadata; create structured chunks with `{text, section, doc_id, page}` |
| txtai + GPT-4 | Not handling token limits - concatenating all retrieved chunks into single prompt | Implement context window management: rank chunks, take top-k that fit within 70% of context limit, reserve 30% for generation |
| Docling table extraction | Assuming extracted Markdown tables are correct without validation | Validate extracted tables: check cell count, numerical value ranges, compare 10-20 sample tables to originals |
| txtai knowledge graph + RAG | Building graph and vector index separately, querying independently | Use txtai's hybrid approach: graph for entity relationships + vector for semantic, combine results with provenance from both |
| LobeChat UI + backend | Streaming responses without source citations - citations added after stream completes | Stream answer + citations together, format as `{chunk: "text", sources: [{doc, page}]}` per chunk |
| txtai embeddings + filtering | Filtering metadata after retrieval (semantic search entire corpus then filter) | Use txtai's metadata filters IN the query: `embeddings.search("query", where="doc_type='specification' AND date>2020")` |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-indexing entire corpus on each document update | POC with 10 docs takes 2 min to re-index, acceptable | Implement incremental indexing: add/update single documents via txtai's upsert capability | > 50 documents or > 100MB corpus |
| No caching layer - every query hits LLM | Works in demo with 5 test queries | Implement semantic caching: if query similar to previous (>0.9 cosine sim), return cached answer | > 20 queries/day or limited LLM API budget |
| Loading all embeddings into memory | Fast retrieval with 10k chunks | Use txtai's database backend (SQLite/DuckDB) for on-disk storage with memory mapping | > 100k chunks or > 2GB embeddings |
| Synchronous document processing | Acceptable with 10 documents taking 10 minutes total | Background job queue for ingestion, status tracking, process documents in parallel | > 20 documents or documents > 50 pages |
| Global knowledge graph (no partitioning) | Graph queries fast with 500 entities | Partition graph by document or domain, query relevant subgraphs first | > 5000 entities or > 20k edges |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Not scoping retrieval by user permissions | RAG system retrieves and exposes text from classified/restricted documents that user shouldn't access | Implement document-level access control: metadata field `{classification: "UNCLASSIFIED"}`, filter retrieved chunks by user clearance BEFORE sending to LLM |
| Storing raw prompts/queries with PII | Logs contain sensitive queries like "What's the failure rate of [classified system]?" | Sanitize logs: hash queries, strip entity names, use query IDs not text for debugging |
| Caching answers without permission checks | User A asks question, system caches answer from restricted doc, User B gets cached answer despite no access | Cache entries must include permission metadata: `cache_key = hash(query + user_permissions)` |
| Returning source text verbatim in answers | LLM copies sensitive specification text directly into response, exposes more than necessary | Implement response filtering: detect and redact classification markings, limit verbatim text length, paraphrase mode for sensitive docs |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Answering unanswerable questions confidently | System hallucinates specs for systems not in corpus, user trusts wrong info | Detect out-of-domain queries: check retrieval scores, if all < threshold, respond "I don't have information about that in the provided documents" |
| Showing chunk text as sources (raw semantic search results) | User sees decontextualized paragraph snippets, can't verify in original doc | Show hierarchical context: "Document Title > Section > Subsection" + page number + preview with highlighting |
| No confidence indicators on answers | All answers look equally trustworthy, user can't distinguish confident vs uncertain | Implement answer confidence scoring: retrieval score + source consistency + uncertainty detection, show confidence level |
| Multi-source answers without attribution per claim | "System X has property Y and constraint Z" - unclear which source says what | Inline citations per sentence: "System X has property Y [Doc A p.12]. Constraint Z applies [Doc B p.45]" |
| Poor handling of follow-up questions | Each question treated independently, loses conversation context | Conversation memory: track previous queries + retrieved docs, expand current query with conversation history |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Document processing:** Often missing validation that extraction succeeded - verify page counts match, tables extracted (not skipped), OCR confidence acceptable
- [ ] **Chunking strategy:** Often missing semantic boundaries - verify chunks don't split mid-sentence, tables kept with context, metadata propagated
- [ ] **Hybrid retrieval:** Often missing normalization - verify BM25 and semantic scores in comparable ranges, neither dominates, test edge cases (exact match queries, conceptual queries)
- [ ] **Knowledge graph:** Often missing entity resolution - verify no duplicate entities (check for "F-16" vs "F16"), relationships validated against source docs
- [ ] **Source attribution:** Often missing page numbers/sections - verify every answer has source metadata, can trace back to exact location in original PDF
- [ ] **Evaluation harness:** Often missing multi-hop queries - verify test set includes cross-document questions, multi-source synthesis, unanswerable queries
- [ ] **Error handling:** Often missing timeout/retry logic - verify Docling failures handled gracefully, retrieval timeouts don't crash, LLM API failures have fallbacks
- [ ] **Answer quality:** Often missing faithfulness checks - verify LLM doesn't add information not in retrieved chunks, no hallucinated specs, cross-document constraints respected

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Poor chunking discovered during evaluation | MEDIUM (4-8 hours) | Re-process documents with better chunking strategy, re-index embeddings, re-run evaluation baseline - ingestion pipeline likely already built, just change chunking parameters |
| Missing source attribution | HIGH (8-16 hours) | Rebuild indexing pipeline to capture metadata, re-index entire corpus, update retrieval logic to propagate sources, modify prompt templates to format citations - touches entire pipeline |
| Hybrid retrieval underperforming | LOW (2-4 hours) | Already have BM25 and semantic working independently, just need tuning: run baseline comparisons, adjust weights/normalization, re-evaluate - no re-indexing needed |
| Knowledge graph quality issues | MEDIUM-HIGH (6-12 hours) | Build entity resolution layer (canonical forms), re-extract relationships with validation prompts, create manual verification set - may need to rebuild graph from scratch |
| Docling extraction failures | MEDIUM (4-8 hours) | Integrate fallback parser (Unstructured, pymupdf), create extraction quality checks, reprocess failed documents - may need to change preprocessing significantly |
| Multi-doc synthesis missing cross-references | HIGH (12-16 hours) | Extract document relationships, build cross-reference graph, modify retrieval to follow references, update generation prompts for multi-doc synthesis - requires architectural change |
| Architecture too monolithic | VERY HIGH (16-24 hours) | Refactor into modules, separate ingestion from query, add persistence layer, rebuild interfaces - essentially rewriting from scratch with same logic |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Context fragmentation from poor chunking | Phase 1: Document Processing Setup | Manually inspect 20-30 chunks - no split sentences, tables with context, metadata present |
| Missing source attribution | Phase 2: Core RAG Pipeline | Test query returns `{answer, sources: [{doc, page, section}]}` - trace back to original PDF location |
| Hybrid retrieval not tuned | Phase 3: Hybrid Retrieval Integration | Baseline measurements show hybrid outperforms single method on 80%+ of test queries |
| Knowledge graph extraction quality | Phase 4: Knowledge Graph Integration | Manual verification: 50-100 random entity-relationship triples correct in source documents |
| Docling failures | Phase 1: Document Processing Setup | Process all ~10 target documents, check page counts, table extraction, no timeouts/errors |
| Multi-doc synthesis issues | Phase 5: Multi-Source Synthesis | Test queries requiring 2+ documents return integrated answers with sources from all docs |
| Architectural shortcuts | Phase 0: Planning & Phase 1: Foundation | Modular design - can test/run ingestion and query pipelines independently |

## Timeline Risk Mitigation for 5-Day POC

**Critical Path Analysis:**
- **Day 1 (24% of timeline):** Document processing + chunking foundation - highest risk, must get right
  - Risk: Docling issues not discovered until too late
  - Mitigation: Test Docling on all target documents FIRST (hour 1-2), have fallback parser ready

- **Day 2 (20% of timeline):** Core RAG + evaluation harness
  - Risk: Skip evaluation to "save time", discover quality issues on Day 5
  - Mitigation: Build minimal eval (30 Q&A pairs) before optimization - saves time overall

- **Day 3 (20% of timeline):** Hybrid retrieval + tuning
  - Risk: Over-engineer tuning, waste entire day on marginal gains
  - Mitigation: Use RRF (no tuning needed), baseline comparison takes 2 hours max

- **Day 4 (18% of timeline):** Knowledge graph integration
  - Risk: Extraction quality issues, knowledge graph adds no value but takes full day
  - Mitigation: Start with 2-3 documents, validate quality before scaling - or skip if not providing value

- **Day 5 (18% of timeline):** UI integration + polish + documentation
  - Risk: Integration breaks working components, no time to debug
  - Mitigation: LobeChat integration tested incrementally Days 2-4, Day 5 only final polish

**De-scoping Priorities (if behind schedule):**
1. **Keep:** Document processing quality, source attribution, basic evaluation, core RAG
2. **Simplify:** Use semantic-only or BM25-only instead of hybrid (can add post-POC)
3. **Skip if needed:** Knowledge graph (highest risk/reward ratio), advanced UI features

## Sources

**General RAG + Knowledge Graph Pitfalls:**
- [How to Solve 5 Common RAG Failures with Knowledge Graphs](https://www.freecodecamp.org/news/how-to-solve-5-common-rag-failures-with-knowledge-graphs/)
- [Hybrid RAG in the Real World: Graphs, BM25, and the End of Black-Box Retrieval](https://community.netapp.com/t5/Tech-ONTAP-Blogs/Hybrid-RAG-in-the-Real-World-Graphs-BM25-and-the-End-of-Black-Box-Retrieval/ba-p/464834)
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them)
- [Diagnosing and Addressing Pitfalls in KG-RAG](https://openreview.net/pdf?id=Vd5JXiX073)

**Technical Document Chunking:**
- [Why Your RAG System Fails on Technical Documents (And How to Fix It)](https://medium.com/@officialchiragp1605/why-your-rag-system-fails-on-technical-documents-and-how-to-fix-it-5c9e5be7948f)
- [The Ultimate Guide to Chunking Strategies for RAG Applications](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089)
- [Document Chunking for RAG: 9 Strategies Tested (70% Accuracy Boost)](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide)

**Hybrid Retrieval:**
- [Understanding Hybrid Search RAG for Better AI Answers](https://www.meilisearch.com/blog/hybrid-search-rag)
- [Hybrid Search: Combining BM25 and Semantic Search](https://lancedb.com/blog/hybrid-search-combining-bm25-and-semantic-search-for-better-results-with-lan-1358038fe7e6/)
- [Building Effective Hybrid Search in OpenSearch](https://opensearch.org/blog/building-effective-hybrid-search-in-opensearch-techniques-and-best-practices/)

**Source Attribution:**
- [Effective Source Tracking in RAG Systems](https://www.chitika.com/source-tracking-rag/)
- [DocIndex: Retrieval-Augmented Generation with Source Traceability](https://keviinkibe.medium.com/docindex-retrieval-augmented-generation-with-source-traceability-fddc3b7441f5)
- [5 Key Features and Benefits of RAG](https://www.microsoft.com/en-us/microsoft-cloud/blog/2025/02/13/5-key-features-and-benefits-of-retrieval-augmented-generation-rag/)

**Document Processing:**
- [PDF Table Extraction Showdown: Docling vs. LlamaParse vs. Unstructured](https://boringbot.substack.com/p/pdf-table-extraction-showdown-docling)
- [Docling vs. LLMWhisperer: Best Docling Alternative in 2026](https://unstract.com/blog/docling-alternative/)
- [PDF Data Extraction Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)

**Multi-Document Synthesis:**
- [How to Build Contextual RAG Systems with Google's NotebookLM](https://ragaboutit.com/how-to-build-contextual-rag-systems-with-googles-notebooklm-the-complete-enterprise-knowledge-synthesis-guide/)
- [How to Build Production-Ready RAG with LangChain's Multi-Document Framework](https://ragaboutit.com/how-to-build-a-production-ready-rag-system-with-langchains-new-multi-document-processing-framework/)

**Knowledge Graph Quality:**
- [Knowledge Graphs for Enhancing LLMs in Entity Disambiguation](https://arxiv.org/html/2505.02737v2)
- [Understanding Effect of KG Extraction Error on Downstream Analyses](https://link.springer.com/article/10.1007/s41109-025-00749-0)

**Production & Scaling:**
- [RAG at Scale: How to Build Production AI Systems in 2026](https://redis.io/blog/rag-at-scale/)
- [Scaling RAG from POC to Production](https://medium.com/data-science/scaling-rag-from-poc-to-production-31bd45d195c8)
- [LLM Security Risks in 2026: Prompt Injection, RAG, and Shadow AI](https://sombrainc.com/blog/llm-security-risks-2026)

**Evaluation:**
- [RAG Evaluation: 2026 Metrics and Benchmarks for Enterprise AI](https://labelyourdata.com/articles/llm-fine-tuning/rag-evaluation)
- [A Complete Guide to RAG Evaluation: Metrics, Testing and Best Practices](https://www.evidentlyai.com/llm-guide/rag-evaluation)

---
*Pitfalls research for: DocRAG POC - IAI Defense Industry Assignment*
*Researched: 2026-01-27*
*Research confidence: MEDIUM-HIGH (verified with 2026 sources, cross-referenced multiple implementations)*
