"""Document relationship graph storage in FalkorDB.

Manages document-level relationships for multi-source synthesis:
- CITES edges for explicit citations between documents
- SHARES_ENTITIES edges for documents with 2+ common entities
"""
from typing import List, Dict, Any, Optional
import structlog
from falkordb import FalkorDB

from app.config import settings
from .schemas import DocumentRelationship

logger = structlog.get_logger(__name__)


class DocumentRelationshipStore:
    """Manages document-level relationship graph in FalkorDB.

    Schema:
    - Nodes: Document (doc_id, filename, user_id, page_count, chunk_count)
    - Edges: CITES (explicit), SHARES_ENTITIES (implicit)
    """

    def __init__(self):
        """Initialize FalkorDB connection (reuses same DB as entity graph)."""
        try:
            url_parts = settings.FALKORDB_URL.replace("redis://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6379

            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(settings.FALKORDB_GRAPH_NAME)

            logger.info("doc_relationship_store_connected", host=host, port=port)
            self.ensure_indexes()

        except Exception as e:
            logger.error("doc_relationship_store_connection_failed", error=str(e))
            raise

    def ensure_indexes(self) -> None:
        """Create indexes on Document node properties."""
        indexes = [
            "CREATE INDEX ON :Document(doc_id)",
            "CREATE INDEX ON :Document(user_id)",
        ]
        for query in indexes:
            try:
                self.graph.query(query)
            except Exception as e:
                if "already indexed" not in str(e).lower():
                    logger.warning("doc_index_warning", query=query, error=str(e))

    def add_document_node(
        self,
        doc_id: str,
        filename: str,
        user_id: str,
        page_count: int = 0,
        chunk_count: int = 0
    ) -> bool:
        """Add or update document node in relationship graph."""
        try:
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
            self.graph.query(query, params=params)
            logger.debug("document_node_added", doc_id=doc_id, filename=filename)
            return True
        except Exception as e:
            logger.error("add_document_node_failed", doc_id=doc_id, error=str(e))
            return False

    def add_relationship(self, rel: DocumentRelationship, user_id: str) -> bool:
        """Add relationship between documents."""
        try:
            edge_type = "CITES" if rel.relationship_type == "explicit_citation" else "SHARES_ENTITIES"

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
                "evidence": rel.evidence
            }
            result = self.graph.query(query, params=params)

            if result.result_set:
                logger.debug("doc_relationship_added",
                           source=rel.source_doc_id,
                           target=rel.target_doc_id,
                           type=rel.relationship_type)
                return True
            return False
        except Exception as e:
            logger.error("add_doc_relationship_failed", error=str(e))
            return False

    def get_related_documents(
        self,
        doc_ids: List[str],
        user_id: str,
        min_strength: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Get documents related to input set (for multi-doc queries)."""
        try:
            query = """
            UNWIND $doc_ids AS source_doc_id
            MATCH (source:Document {doc_id: source_doc_id, user_id: $user_id})
            MATCH (source)-[r]-(related:Document)
            WHERE r.strength >= $min_strength AND related.user_id = $user_id
            RETURN DISTINCT related.doc_id as doc_id,
                   related.filename as filename,
                   r.strength as strength,
                   type(r) as relationship_type
            ORDER BY r.strength DESC
            """
            params = {
                "doc_ids": doc_ids,
                "user_id": user_id,
                "min_strength": min_strength
            }
            result = self.graph.query(query, params=params)

            return [
                {
                    "doc_id": row[0],
                    "filename": row[1],
                    "strength": row[2],
                    "relationship_type": row[3]
                }
                for row in result.result_set
            ]
        except Exception as e:
            logger.error("get_related_documents_failed", error=str(e))
            return []

    def get_all_relationships(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all document relationships for a user (for debug endpoint)."""
        try:
            query = """
            MATCH (source:Document {user_id: $user_id})-[r]->(target:Document)
            RETURN source.doc_id as source_doc_id,
                   source.filename as source_filename,
                   target.doc_id as target_doc_id,
                   target.filename as target_filename,
                   type(r) as relationship_type,
                   r.strength as strength,
                   r.evidence as evidence
            """
            params = {"user_id": user_id}
            result = self.graph.query(query, params=params)

            return [
                {
                    "source_doc_id": row[0],
                    "source_filename": row[1],
                    "target_doc_id": row[2],
                    "target_filename": row[3],
                    "relationship_type": row[4],
                    "strength": row[5],
                    "evidence": row[6]
                }
                for row in result.result_set
            ]
        except Exception as e:
            logger.error("get_all_relationships_failed", error=str(e))
            return []

    def delete_document_relationships(self, doc_id: str, user_id: str) -> int:
        """Delete document node and all its relationships (for re-ingestion)."""
        try:
            query = """
            MATCH (d:Document {doc_id: $doc_id, user_id: $user_id})
            DETACH DELETE d
            RETURN count(d) as deleted
            """
            params = {"doc_id": doc_id, "user_id": user_id}
            result = self.graph.query(query, params=params)

            deleted = result.result_set[0][0] if result.result_set else 0
            logger.info("document_relationships_deleted", doc_id=doc_id, deleted=deleted)
            return deleted
        except Exception as e:
            logger.error("delete_document_relationships_failed", error=str(e))
            return 0

    def count_relationships(self, user_id: str) -> Dict[str, int]:
        """Count document relationships by type."""
        try:
            query = """
            MATCH (a:Document {user_id: $user_id})-[r]->(b:Document)
            RETURN type(r) as rel_type, count(r) as count
            """
            params = {"user_id": user_id}
            result = self.graph.query(query, params=params)

            counts = {"cites": 0, "shares_entities": 0}
            for row in result.result_set:
                rel_type = row[0].lower()
                counts[rel_type] = row[1]
            return counts
        except Exception as e:
            logger.error("count_doc_relationships_failed", error=str(e))
            return {"cites": 0, "shares_entities": 0}
