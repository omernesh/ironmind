# IRONMIND Example Queries

This document provides example queries demonstrating IRONMIND's capabilities with technical documentation.

## Example 1: Basic Information Retrieval

**Query:** "What are the primary network layers described in the system architecture?"

**Expected Answer:**
> The system architecture consists of three primary network layers [1]:
> 1. Edge Layer - handles device connectivity
> 2. Core Layer - manages data routing
> 3. Management Layer - provides monitoring and control
>
> [1] FC-001-System-Architecture.docx, p.12-14

**Why it works:**
- Hybrid retrieval finds chunks mentioning "network layers" and "architecture"
- Reranking prioritizes the most relevant section
- Citation provides exact source for verification

---

## Example 2: Multi-Document Synthesis

**Query:** "How do the power system and navigation module interact according to the documentation?"

**Expected Answer:**
> Based on multiple documents, the power system and navigation module interact through:
>
> **Power Supply Interface [1]:**
> The navigation module requires 28V DC from the primary power bus...
>
> **Data Communication [2]:**
> Navigation data is transmitted via MIL-STD-1553 bus to the power management unit...
>
> Both documents confirm the critical dependency on stable power for navigation accuracy [1,2].
>
> [1] FC-020-Power-System.docx, p.8
> [2] FC-035-Navigation-Module.docx, p.15

**Why it works:**
- Multi-source synthesis detected (2+ documents)
- Topic-organized response groups related information
- Citations indicate which source supports each claim

---

## Example 3: Knowledge Graph Query

**Query:** "What components depend on the main controller?"

**Expected Answer:**
> Based on the documentation and component relationships [1,2]:
>
> The following components depend on the main controller:
> - Sensor Array (data processing dependency)
> - Display Unit (command interface)
> - Communication Module (timing synchronization)
>
> The main controller provides the central coordination point for all subsystem operations [1].
>
> [1] FC-001-System-Architecture.docx, p.23
> [2] Knowledge Graph - Main Controller

**Why it works:**
- Graph retrieval finds entities with "depends_on" relationships
- Combines document chunks with graph-derived knowledge
- Citation [2] transparently indicates graph-sourced information

---

## Example 4: Troubleshooting Query

**Query:** "What error codes indicate a sensor calibration failure?"

**Expected Answer:**
> According to the error code reference [1], sensor calibration failures are indicated by:
>
> | Code | Description |
> |------|-------------|
> | E-CAL-001 | Calibration timeout |
> | E-CAL-002 | Reference signal out of range |
> | E-CAL-003 | Sensor drift exceeds threshold |
>
> Recommended resolution: Follow the recalibration procedure in Section 5.3 [1].
>
> [1] FC-050-Maintenance-Guide.docx, p.45-46

**Why it works:**
- BM25 component excels at finding specific codes/terms
- Hybrid retrieval ensures both semantic and keyword matches
- Structured information (tables) preserved from source

---

## Example 5: Handling Unknown Information

**Query:** "What is the operating temperature range for the XYZ-9000 module?"

**Expected Answer:**
> I couldn't find specific information about the "XYZ-9000 module" in your uploaded documents.
>
> The available documentation covers the following modules:
> - ABC Controller (FC-001)
> - Navigation Unit (FC-035)
> - Power System (FC-020)
>
> Please check if this component is documented under a different name, or upload the relevant specification document.

**Why it works:**
- System acknowledges lack of information rather than hallucinating
- Provides helpful context about available documents
- Suggests actionable next steps

---

## Query Tips

1. **Be specific:** "power consumption of the navigation module" > "power stuff"
2. **Use technical terms:** System handles acronyms and codes well
3. **Ask about relationships:** "How does X connect to Y?" leverages knowledge graph
4. **Multi-document questions:** System synthesizes across all your uploaded docs

## Limitations

- Answers only from uploaded documents (no external knowledge)
- Complex multi-hop reasoning may require multiple queries
- Very large documents (100+ pages) may have retrieval gaps
- Scanned PDFs with poor OCR quality affect accuracy
