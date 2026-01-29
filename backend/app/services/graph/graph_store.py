"""FalkorDB client wrapper for knowledge graph storage and retrieval.

Provides CRUD operations for entities and relationships, multi-hop traversal,
and user-scoped graph isolation for multi-tenant support.
"""
from typing import Optional, Dict, List, Any
import structlog
from falkordb import FalkorDB

from app.config import settings
from .schemas import Entity, Relationship


logger = structlog.get_logger(__name__)


class GraphStore:
    """FalkorDB client wrapper for graph operations.

    Manages entity/relationship storage with user isolation and provides
    graph traversal capabilities for knowledge graph-aware retrieval.
    """

    def __init__(self):
        """Initialize FalkorDB connection and ensure indexes exist."""
        try:
            # Parse URL - FalkorDB uses Redis protocol
            # Format: redis://host:port
            url_parts = settings.FALKORDB_URL.replace("redis://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6379

            # Connect to FalkorDB
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(settings.FALKORDB_GRAPH_NAME)

            logger.info(
                "falkordb_connected",
                host=host,
                port=port,
                graph_name=settings.FALKORDB_GRAPH_NAME
            )

            # Create indexes for query performance
            self.ensure_indexes()

        except Exception as e:
            logger.error(
                "falkordb_connection_failed",
                error=str(e),
                url=settings.FALKORDB_URL
            )
            raise

    def ensure_indexes(self) -> None:
        """Create indexes on entity properties for query performance.

        Indexes enable fast lookups by name, type, and user_id.
        Should be called once during initialization.
        """
        try:
            # FalkorDB index syntax: CREATE INDEX ON :Label(property)
            indexes = [
                "CREATE INDEX ON :Entity(name)",
                "CREATE INDEX ON :Entity(type)",
                "CREATE INDEX ON :Entity(user_id)",
            ]

            for index_query in indexes:
                try:
                    self.graph.query(index_query)
                except Exception as e:
                    # Index might already exist - ignore duplicate errors
                    if "already indexed" not in str(e).lower():
                        logger.warning(
                            "index_creation_warning",
                            query=index_query,
                            error=str(e)
                        )

            logger.info("indexes_ensured", count=len(indexes))

        except Exception as e:
            logger.error("index_creation_failed", error=str(e))
            # Don't raise - indexes are performance optimization, not critical

    def add_entity(self, entity: Entity, user_id: str) -> bool:
        """Add or update entity in the graph.

        Uses MERGE to prevent duplicates (upsert by name + user_id).

        Args:
            entity: Entity schema with properties
            user_id: User identifier for multi-tenant isolation

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use MERGE for upsert (create if not exists, update if exists)
            # Parameterized query for safety
            query = """
            MERGE (e:Entity {name: $name, user_id: $user_id})
            SET e.type = $type,
                e.description = $description,
                e.parent_entity = $parent_entity,
                e.doc_id = $doc_id,
                e.chunk_id = $chunk_id
            RETURN e
            """

            params = {
                "name": entity.name,
                "user_id": user_id,
                "type": entity.type,
                "description": entity.description,
                "parent_entity": entity.parent_entity,
                "doc_id": entity.doc_id,
                "chunk_id": entity.chunk_id,
            }

            result = self.graph.query(query, params=params)

            logger.debug(
                "entity_added",
                entity_name=entity.name,
                entity_type=entity.type,
                user_id=user_id
            )

            return True

        except Exception as e:
            logger.error(
                "add_entity_failed",
                entity_name=entity.name,
                error=str(e),
                user_id=user_id
            )
            return False

    def add_relationship(self, rel: Relationship, user_id: str) -> bool:
        """Add relationship between two entities.

        Only creates relationship if both source and target entities exist
        for the given user_id.

        Args:
            rel: Relationship schema
            user_id: User identifier for multi-tenant isolation

        Returns:
            True if successful, False if source/target don't exist or error
        """
        try:
            # Match both entities first to ensure they exist
            # Use dynamic relationship type from schema
            query = """
            MATCH (source:Entity {name: $source_name, user_id: $user_id})
            MATCH (target:Entity {name: $target_name, user_id: $user_id})
            MERGE (source)-[r:RELATES_TO {type: $rel_type}]->(target)
            SET r.context = $context,
                r.doc_id = $doc_id
            RETURN r
            """

            params = {
                "source_name": rel.source_entity,
                "target_name": rel.target_entity,
                "user_id": user_id,
                "rel_type": rel.relationship_type,
                "context": rel.context,
                "doc_id": rel.doc_id,
            }

            result = self.graph.query(query, params=params)

            # Check if relationship was created
            if result.result_set:
                logger.debug(
                    "relationship_added",
                    source=rel.source_entity,
                    target=rel.target_entity,
                    type=rel.relationship_type,
                    user_id=user_id
                )
                return True
            else:
                logger.warning(
                    "relationship_skipped_missing_entities",
                    source=rel.source_entity,
                    target=rel.target_entity,
                    user_id=user_id
                )
                return False

        except Exception as e:
            logger.error(
                "add_relationship_failed",
                source=rel.source_entity,
                target=rel.target_entity,
                error=str(e),
                user_id=user_id
            )
            return False

    def get_entity(self, name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity by name for specific user.

        Args:
            name: Entity name
            user_id: User identifier for isolation

        Returns:
            Entity properties as dict, or None if not found
        """
        try:
            query = """
            MATCH (e:Entity {name: $name, user_id: $user_id})
            RETURN e
            """

            params = {"name": name, "user_id": user_id}
            result = self.graph.query(query, params=params)

            if result.result_set and len(result.result_set) > 0:
                # Extract node properties
                node = result.result_set[0][0]
                return dict(node.properties)

            return None

        except Exception as e:
            logger.error(
                "get_entity_failed",
                entity_name=name,
                error=str(e),
                user_id=user_id
            )
            return None

    def get_subgraph(
        self,
        entity_name: str,
        user_id: str,
        depth: int = 2,
        limit: int = 50
    ) -> Dict[str, List[Dict]]:
        """Retrieve subgraph around entity using BFS traversal.

        Args:
            entity_name: Starting entity name
            user_id: User identifier for isolation
            depth: Maximum traversal depth (hops). Default: 2
            limit: Maximum total nodes to return. Default: 50

        Returns:
            Dict with "nodes" and "edges" lists containing subgraph
        """
        try:
            # BFS traversal with configurable depth
            # Query returns nodes and relationships separately for easier parsing
            query = f"""
            MATCH path = (start:Entity {{name: $name, user_id: $user_id}})-[r*0..{depth}]-(connected)
            WHERE connected.user_id = $user_id
            WITH DISTINCT connected, relationships(path) as rels
            RETURN connected, rels
            LIMIT $limit
            """

            params = {
                "name": entity_name,
                "user_id": user_id,
                "limit": limit
            }

            result = self.graph.query(query, params=params)

            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()
            node_id_to_name = {}  # Map node IDs to names for edge construction

            for record in result.result_set:
                # Extract node
                node = record[0]
                node_name = node.properties.get("name")
                node_id_to_name[node.id] = node_name

                if node_name not in seen_nodes:
                    nodes.append(dict(node.properties))
                    seen_nodes.add(node_name)

                # Extract relationships from path
                relationships = record[1] if len(record) > 1 else []
                if relationships:
                    for rel in relationships:
                        # Create unique edge identifier
                        edge_id = f"{rel.src_node}-{rel.dest_node}-{rel.relation}"
                        if edge_id not in seen_edges:
                            # Note: src_node and dest_node are IDs, not names
                            # We'll need to query for node names or build a mapping
                            edges.append({
                                "source_id": rel.src_node,
                                "target_id": rel.dest_node,
                                "relationship": rel.relation,
                                "type": rel.properties.get("type", "unknown"),
                                "context": rel.properties.get("context", ""),
                                "doc_id": rel.properties.get("doc_id", "")
                            })
                            seen_edges.add(edge_id)

            # Build node ID to name mapping by querying all nodes in result
            # Then update edge source/target from IDs to names
            if edges:
                # Get all unique node IDs from edges
                all_node_ids = set()
                for edge in edges:
                    all_node_ids.add(edge["source_id"])
                    all_node_ids.add(edge["target_id"])

                # Query to get names for these IDs
                for node_id in all_node_ids:
                    if node_id not in node_id_to_name:
                        # Query node by ID
                        id_query = f"""
                        MATCH (n:Entity)
                        WHERE ID(n) = {node_id} AND n.user_id = $user_id
                        RETURN n
                        """
                        id_result = self.graph.query(id_query, params={"user_id": user_id})
                        if id_result.result_set:
                            node_id_to_name[node_id] = id_result.result_set[0][0].properties.get("name")

                # Update edges with node names
                for edge in edges:
                    edge["source"] = node_id_to_name.get(edge["source_id"], f"node_{edge['source_id']}")
                    edge["target"] = node_id_to_name.get(edge["target_id"], f"node_{edge['target_id']}")
                    # Remove ID fields
                    del edge["source_id"]
                    del edge["target_id"]
                    del edge["relationship"]  # Keep only the type field

            logger.info(
                "subgraph_retrieved",
                entity=entity_name,
                depth=depth,
                nodes_count=len(nodes),
                edges_count=len(edges),
                user_id=user_id
            )

            return {
                "nodes": nodes,
                "edges": edges
            }

        except Exception as e:
            logger.error(
                "get_subgraph_failed",
                entity=entity_name,
                error=str(e),
                user_id=user_id
            )
            return {"nodes": [], "edges": []}

    def delete_document_entities(self, doc_id: str, user_id: str) -> int:
        """Delete all entities and relationships from a specific document.

        Used for document re-ingestion to remove stale graph data.

        Args:
            doc_id: Document identifier
            user_id: User identifier for isolation

        Returns:
            Number of entities deleted
        """
        try:
            # DETACH DELETE removes node and all its relationships
            query = """
            MATCH (e:Entity {doc_id: $doc_id, user_id: $user_id})
            DETACH DELETE e
            RETURN count(e) as deleted_count
            """

            params = {"doc_id": doc_id, "user_id": user_id}
            result = self.graph.query(query, params=params)

            deleted_count = 0
            if result.result_set and len(result.result_set) > 0:
                deleted_count = result.result_set[0][0]

            logger.info(
                "document_entities_deleted",
                doc_id=doc_id,
                deleted_count=deleted_count,
                user_id=user_id
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "delete_document_entities_failed",
                doc_id=doc_id,
                error=str(e),
                user_id=user_id
            )
            return 0
