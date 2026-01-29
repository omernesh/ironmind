"""Cross-reference detection for document relationship graph.

Detects two types of document relationships:
1. Explicit citations: Document codes, "See Document X", hyperlinks
2. Shared entities: Documents with 2+ common entities (from knowledge graph)
"""
import re
from typing import List, Dict, Any, Set, Optional
import structlog

try:
    from Levenshtein import ratio as levenshtein_ratio
except ImportError:
    # Fallback if python-Levenshtein not installed
    def levenshtein_ratio(s1: str, s2: str) -> float:
        # Simple ratio based on length difference
        if not s1 or not s2:
            return 0.0
        return 1.0 - abs(len(s1) - len(s2)) / max(len(s1), len(s2))

from app.services.graph.schemas import DocumentRelationship
from app.services.graph.graph_store import GraphStore
from app.services.retriever import ACRONYM_MAP

logger = structlog.get_logger(__name__)


class CrossReferenceDetector:
    """Detects cross-references between documents using dual signals.

    Priority: Explicit citations (strength 1.0) > Shared entities (strength 0.5-0.9)
    Threshold: Requires 2+ shared entities to establish shared_entities relationship.
    """

    # Patterns for explicit citation detection
    DOC_CODE_PATTERN = re.compile(r'\b[A-Z]{2,}-[\d\.]+\b')  # FC-001, GC-v2.3
    SEE_DOC_PATTERN = re.compile(
        r'(?:see|refer to|described in|detailed in|according to)\s+([A-Za-z\s\-]+(?:manual|guide|specification|document|spec))',
        re.IGNORECASE
    )
    SECTION_REF_PATTERN = re.compile(
        r'section\s+[\d\.]+\s+of\s+([A-Za-z\s\-]+)',
        re.IGNORECASE
    )

    def __init__(self):
        self.graph_store = GraphStore()

    async def detect_cross_references(
        self,
        doc_id: str,
        doc_text: str,
        user_id: str,
        existing_docs: List[Dict[str, Any]]
    ) -> List[DocumentRelationship]:
        """
        Detect relationships between new document and existing documents.

        Args:
            doc_id: ID of document being ingested
            doc_text: Full text content of document
            user_id: User identifier for isolation
            existing_docs: List of existing documents [{doc_id, filename}]

        Returns:
            List of DocumentRelationship objects
        """
        relationships = []

        # Signal 1: Explicit citations (STRONGER - weight 1.0)
        explicit_refs = self._detect_explicit_references(doc_text, existing_docs)
        for ref in explicit_refs:
            relationships.append(DocumentRelationship(
                source_doc_id=doc_id,
                target_doc_id=ref["target_doc_id"],
                relationship_type="explicit_citation",
                strength=1.0,
                evidence=[ref["citation_text"]]
            ))

        # Signal 2: Shared entities (WEAKER - weight 0.5-0.9)
        shared_entity_refs = await self._detect_shared_entities(
            doc_id, user_id, existing_docs
        )
        for ref in shared_entity_refs:
            # Skip if already have explicit citation to this doc
            if any(r.target_doc_id == ref["target_doc_id"] and
                   r.relationship_type == "explicit_citation"
                   for r in relationships):
                continue

            relationships.append(DocumentRelationship(
                source_doc_id=doc_id,
                target_doc_id=ref["target_doc_id"],
                relationship_type="shared_entities",
                strength=ref["strength"],
                evidence=ref["shared_entities"]
            ))

        logger.info(
            "cross_references_detected",
            doc_id=doc_id,
            explicit_count=len(explicit_refs),
            shared_entity_count=len(shared_entity_refs),
            total_relationships=len(relationships)
        )

        return relationships

    def _detect_explicit_references(
        self,
        text: str,
        existing_docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect explicit document citations using pattern matching."""
        refs = []
        all_mentions = []

        # Pattern 1: Document codes (FC-001, GC-v2.3)
        codes = self.DOC_CODE_PATTERN.findall(text)
        all_mentions.extend(codes)

        # Pattern 2: "See [document name]" patterns
        see_refs = self.SEE_DOC_PATTERN.findall(text)
        all_mentions.extend(see_refs)

        # Pattern 3: Section references
        section_refs = self.SECTION_REF_PATTERN.findall(text)
        all_mentions.extend(section_refs)

        # Match against existing document filenames using fuzzy matching
        for mention in all_mentions:
            mention_clean = mention.strip().lower()
            for doc in existing_docs:
                filename = doc.get("filename", "").lower()
                # Remove extension for comparison
                filename_base = re.sub(r'\.[^.]+$', '', filename)

                # Fuzzy match (70% similarity threshold)
                similarity = levenshtein_ratio(mention_clean, filename_base)
                if similarity > 0.7:
                    refs.append({
                        "target_doc_id": doc["doc_id"],
                        "citation_text": mention,
                        "similarity": similarity
                    })
                    break

                # Also check if mention appears in filename
                if mention_clean in filename_base or filename_base in mention_clean:
                    refs.append({
                        "target_doc_id": doc["doc_id"],
                        "citation_text": mention,
                        "similarity": 0.8
                    })
                    break

        # Deduplicate by target_doc_id
        seen = set()
        unique_refs = []
        for ref in refs:
            if ref["target_doc_id"] not in seen:
                unique_refs.append(ref)
                seen.add(ref["target_doc_id"])

        return unique_refs

    async def _detect_shared_entities(
        self,
        doc_id: str,
        user_id: str,
        existing_docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect shared entity relationships (2+ common entities threshold)."""
        refs = []

        # Get entities for the new document
        source_entities = self.graph_store.list_entities_for_doc(doc_id, user_id)
        if not source_entities:
            return refs

        source_names = self._normalize_entity_names(source_entities)

        for target_doc in existing_docs:
            target_doc_id = target_doc["doc_id"]
            if target_doc_id == doc_id:
                continue

            # Get entities for target document
            target_entities = self.graph_store.list_entities_for_doc(target_doc_id, user_id)
            if not target_entities:
                continue

            target_names = self._normalize_entity_names(target_entities)

            # Find shared entities (exact match or alias match)
            shared = source_names & target_names
            shared_list = list(shared)

            # Require 2+ shared entities (per CONTEXT.md decision)
            if len(shared_list) >= 2:
                # Strength based on count: 0.5 + (count - 2) * 0.1, capped at 0.9
                strength = min(0.5 + (len(shared_list) - 2) * 0.1, 0.9)

                refs.append({
                    "target_doc_id": target_doc_id,
                    "shared_entities": shared_list[:10],  # Cap evidence list
                    "strength": strength
                })

        return refs

    def _normalize_entity_names(self, entities: List[Dict]) -> Set[str]:
        """Normalize entity names with acronym expansion for matching."""
        names = set()
        for entity in entities:
            name = entity.get("name", "").lower()
            names.add(name)

            # Add expanded acronym form
            name_upper = entity.get("name", "")
            if name_upper in ACRONYM_MAP:
                names.add(ACRONYM_MAP[name_upper].lower())

            # Also check if name IS an expansion, add acronym
            for acronym, expansion in ACRONYM_MAP.items():
                if expansion.lower() == name:
                    names.add(acronym.lower())

        return names
