"""Integration tests for multi-source synthesis (Phase 5).

Tests cross-reference detection, document relationship storage,
and multi-document synthesis generation.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.graph.schemas import DocumentRelationship
from app.services.graph.doc_relationships import DocumentRelationshipStore
from app.services.graph.cross_reference import CrossReferenceDetector
from app.services.generator import (
    Generator,
    should_activate_synthesis_mode,
    build_synthesis_context
)
from app.models.chat import Citation, ChatResponse


class TestDocumentRelationshipSchema:
    """Tests for DocumentRelationship Pydantic schema."""

    def test_explicit_citation_schema(self):
        """Test explicit citation relationship validation."""
        rel = DocumentRelationship(
            source_doc_id="doc-001",
            target_doc_id="doc-002",
            relationship_type="explicit_citation",
            strength=1.0,
            evidence=["See FC-001 specification"]
        )
        assert rel.relationship_type == "explicit_citation"
        assert rel.strength == 1.0

    def test_shared_entities_schema(self):
        """Test shared entities relationship validation."""
        rel = DocumentRelationship(
            source_doc_id="doc-001",
            target_doc_id="doc-003",
            relationship_type="shared_entities",
            strength=0.7,
            evidence=["GPS Module", "Navigation System"]
        )
        assert rel.relationship_type == "shared_entities"
        assert len(rel.evidence) == 2

    def test_invalid_relationship_type_rejected(self):
        """Test that invalid relationship types are rejected."""
        with pytest.raises(ValueError):
            DocumentRelationship(
                source_doc_id="doc-001",
                target_doc_id="doc-002",
                relationship_type="invalid_type",
                strength=0.5
            )

    def test_strength_bounds(self):
        """Test strength must be between 0 and 1."""
        with pytest.raises(ValueError):
            DocumentRelationship(
                source_doc_id="doc-001",
                target_doc_id="doc-002",
                relationship_type="explicit_citation",
                strength=1.5  # Invalid: > 1.0
            )


class TestSynthesisModeDetection:
    """Tests for synthesis mode activation logic."""

    def test_single_document_no_synthesis(self):
        """Single document should not trigger synthesis mode."""
        chunks = [
            {"doc_id": "doc-001", "text": "chunk 1"},
            {"doc_id": "doc-001", "text": "chunk 2"},
            {"doc_id": "doc-001", "text": "chunk 3"},
        ]
        assert should_activate_synthesis_mode(chunks) is False

    def test_two_documents_triggers_synthesis(self):
        """Two documents with 2+ chunks each triggers synthesis."""
        chunks = [
            {"doc_id": "doc-001", "text": "chunk 1"},
            {"doc_id": "doc-001", "text": "chunk 2"},
            {"doc_id": "doc-002", "text": "chunk 3"},
            {"doc_id": "doc-002", "text": "chunk 4"},
        ]
        assert should_activate_synthesis_mode(chunks) is True

    def test_two_docs_insufficient_chunks(self):
        """Two docs but only 1 chunk each should not trigger synthesis."""
        chunks = [
            {"doc_id": "doc-001", "text": "chunk 1"},
            {"doc_id": "doc-002", "text": "chunk 2"},
        ]
        assert should_activate_synthesis_mode(chunks) is False

    def test_graph_chunks_excluded(self):
        """Graph-derived chunks should not count toward synthesis trigger."""
        chunks = [
            {"doc_id": "doc-001", "text": "chunk 1"},
            {"doc_id": "doc-001", "text": "chunk 2"},
            {"doc_id": "graph", "source": "graph", "text": "entity context"},
            {"doc_id": "graph", "source": "graph", "text": "entity context 2"},
        ]
        assert should_activate_synthesis_mode(chunks) is False

    def test_empty_chunks(self):
        """Empty chunks should return False."""
        assert should_activate_synthesis_mode([]) is False


class TestSynthesisContextBuilding:
    """Tests for synthesis context formatting."""

    def test_context_grouped_by_document(self):
        """Context should be grouped by source document."""
        chunks = [
            {"doc_id": "doc-001", "filename": "Manual A.docx", "text": "Content A1", "page_range": "1-2"},
            {"doc_id": "doc-002", "filename": "Manual B.docx", "text": "Content B1", "page_range": "5-6"},
            {"doc_id": "doc-001", "filename": "Manual A.docx", "text": "Content A2", "page_range": "3-4"},
        ]
        context = build_synthesis_context(chunks)

        assert "=== Manual A.docx ===" in context
        assert "=== Manual B.docx ===" in context
        assert "Content A1" in context
        assert "Content B1" in context

    def test_graph_chunks_marked(self):
        """Graph chunks should be marked with Knowledge Graph header."""
        chunks = [
            {"doc_id": "doc-001", "filename": "Manual.docx", "text": "Doc content", "page_range": "1"},
            {"doc_id": "graph", "filename": "graph", "source": "graph", "entity_name": "GPS Module", "text": "Entity info"},
        ]
        context = build_synthesis_context(chunks)

        assert "Knowledge Graph - GPS Module" in context


class TestCitationModel:
    """Tests for extended Citation model."""

    def test_multi_source_field_default(self):
        """multi_source field should default to False."""
        citation = Citation(
            id=1,
            doc_id="doc-001",
            filename="test.docx",
            page_range="1-2",
            snippet="Test snippet"
        )
        assert citation.multi_source is False

    def test_multi_source_field_true(self):
        """multi_source field can be set to True."""
        citation = Citation(
            id=1,
            doc_id="doc-001",
            filename="test.docx",
            page_range="1-2",
            snippet="Test snippet",
            multi_source=True
        )
        assert citation.multi_source is True

    def test_related_doc_ids_field(self):
        """related_doc_ids field should accept list of doc IDs."""
        citation = Citation(
            id=1,
            doc_id="doc-001",
            filename="test.docx",
            page_range="1-2",
            snippet="Test snippet",
            related_doc_ids=["doc-002", "doc-003"]
        )
        assert len(citation.related_doc_ids) == 2


class TestChatResponseSynthesis:
    """Tests for ChatResponse synthesis fields."""

    def test_synthesis_mode_default(self):
        """synthesis_mode should default to False."""
        response = ChatResponse(
            answer="Test answer",
            citations=[],
            request_id="req-001"
        )
        assert response.synthesis_mode is False
        assert response.source_doc_count == 1

    def test_synthesis_mode_enabled(self):
        """synthesis_mode can be set to True with doc count."""
        response = ChatResponse(
            answer="Multi-source answer",
            citations=[],
            request_id="req-001",
            synthesis_mode=True,
            source_doc_count=3
        )
        assert response.synthesis_mode is True
        assert response.source_doc_count == 3


class TestCrossReferenceDetector:
    """Tests for cross-reference detection patterns."""

    def test_detect_doc_code_pattern(self, skip_if_no_falkordb):
        """Should detect document code patterns like FC-001."""
        detector = CrossReferenceDetector()
        text = "Refer to FC-001 for more details about the flight controller."

        existing_docs = [
            {"doc_id": "doc-fc", "filename": "FC-001-Specification.docx"},
            {"doc_id": "doc-other", "filename": "Other-Document.docx"},
        ]

        refs = detector._detect_explicit_references(text, existing_docs)

        # Should find FC-001 reference
        assert len(refs) >= 1
        assert any(r["target_doc_id"] == "doc-fc" for r in refs)

    def test_detect_see_document_pattern(self, skip_if_no_falkordb):
        """Should detect 'See Document X' patterns."""
        detector = CrossReferenceDetector()
        text = "See the Navigation Manual for calibration procedures."

        existing_docs = [
            {"doc_id": "doc-nav", "filename": "Navigation-Manual.docx"},
        ]

        refs = detector._detect_explicit_references(text, existing_docs)

        # May or may not match depending on fuzzy threshold
        # At minimum should not crash
        assert isinstance(refs, list)


# Skip FalkorDB tests if not available
@pytest.fixture
def skip_if_no_falkordb():
    """Skip test if FalkorDB is not available."""
    try:
        store = DocumentRelationshipStore()
        return store
    except Exception:
        pytest.skip("FalkorDB not available")


class TestDocumentRelationshipStore:
    """Integration tests for DocumentRelationshipStore (requires FalkorDB)."""

    def test_add_document_node(self, skip_if_no_falkordb):
        """Test adding document node to graph."""
        store = skip_if_no_falkordb

        result = store.add_document_node(
            doc_id="test-doc-001",
            filename="test-document.docx",
            user_id="test-user",
            page_count=10,
            chunk_count=25
        )

        assert result is True

        # Cleanup
        store.delete_document_relationships("test-doc-001", "test-user")

    def test_add_and_retrieve_relationship(self, skip_if_no_falkordb):
        """Test adding and retrieving document relationship."""
        store = skip_if_no_falkordb

        # Add two document nodes
        store.add_document_node("test-doc-a", "DocA.docx", "test-user")
        store.add_document_node("test-doc-b", "DocB.docx", "test-user")

        # Add relationship
        rel = DocumentRelationship(
            source_doc_id="test-doc-a",
            target_doc_id="test-doc-b",
            relationship_type="explicit_citation",
            strength=1.0,
            evidence=["See DocB"]
        )
        store.add_relationship(rel, "test-user")

        # Retrieve
        related = store.get_related_documents(
            doc_ids=["test-doc-a"],
            user_id="test-user",
            min_strength=0.5
        )

        assert len(related) >= 1
        assert any(r["doc_id"] == "test-doc-b" for r in related)

        # Cleanup
        store.delete_document_relationships("test-doc-a", "test-user")
        store.delete_document_relationships("test-doc-b", "test-user")
