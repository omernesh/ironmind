"""Graph-aware retrieval service for knowledge graph context expansion.

This service extracts entities from queries and expands context via graph traversal,
enabling relationship-based question answering.
"""
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from app.config import settings
from app.core.logging import get_logger
from app.services.graph.graph_store import GraphStore

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from app.services.graph.extractor import EntityExtractor

logger = get_logger()


class GraphRetriever:
    """
    Graph-aware retrieval for relationship-based queries.

    Extracts entities from user queries and expands context through
    knowledge graph traversal to answer multi-component questions like
    "how does X connect to Y?" or "what depends on Z?"
    """

    def __init__(
        self,
        graph_store: Optional[GraphStore] = None,
        extractor: Optional["EntityExtractor"] = None
    ):
        """Initialize GraphRetriever with dependencies.

        Args:
            graph_store: GraphStore instance for graph queries (uses default if None)
            extractor: EntityExtractor for entity extraction (uses default if None)
        """
        self.graph_store = graph_store or GraphStore()

        # Lazy import to avoid circular dependency
        if extractor is None:
            from app.services.graph.extractor import EntityExtractor
            extractor = EntityExtractor()

        self.extractor = extractor
        self.traversal_depth = settings.GRAPH_TRAVERSAL_DEPTH

    async def extract_query_entities(self, query: str) -> List[str]:
        """Extract entity names mentioned in the query.

        Uses EntityExtractor to identify aerospace/defense entities
        in the user's question.

        Args:
            query: User's question text

        Returns:
            List of entity names found in query (empty if none found)
        """
        try:
            # Use EntityExtractor with dummy IDs for query analysis
            extraction = await self.extractor.extract_from_chunk(
                chunk_text=query,
                doc_id="query",
                chunk_id="query"
            )

            # Return list of entity names
            entity_names = [entity.name for entity in extraction.entities]

            logger.debug("query_entities_extracted",
                        query=query[:100],
                        entity_count=len(entity_names),
                        entities=entity_names)

            return entity_names

        except Exception as e:
            logger.warning("query_entity_extraction_failed",
                          query=query[:100],
                          error=str(e))
            return []

    def is_relationship_query(self, query: str) -> bool:
        """Detect if query is relationship-focused.

        Relationship queries ask about connections, dependencies, or interactions
        between entities and require deeper graph traversal.

        Args:
            query: User's question text

        Returns:
            True if query is relationship-focused (use depth=2)
            False if simple factual query (use depth=1)
        """
        # Keywords indicating relationship focus
        relationship_keywords = [
            "connect", "depend", "configure", "interface", "relate",
            "work with", "interact", "communicate", "link",
            "how does", "what connects", "what depends", "relationship"
        ]

        query_lower = query.lower()

        # Check for relationship keywords
        has_relationship_keyword = any(
            keyword in query_lower for keyword in relationship_keywords
        )

        # Check for multiple entity mentions (heuristic: multiple capitalized words)
        # Exclude common question words and single-letter words
        import re
        question_words = {'what', 'how', 'when', 'where', 'who', 'why', 'which', 'is', 'are', 'does', 'do', 'can'}
        capitalized_words = re.findall(r'\b[A-Z][A-Za-z]+\b', query)
        # Filter out question words at start of sentence
        entity_words = [word for word in capitalized_words if word.lower() not in question_words]
        has_multiple_entities = len(entity_words) >= 2

        is_relationship = has_relationship_keyword or has_multiple_entities

        logger.debug("relationship_query_detection",
                    query=query[:100],
                    is_relationship=is_relationship,
                    keyword_match=has_relationship_keyword,
                    entity_count=len(entity_words))

        return is_relationship

    def format_relationship_context(
        self,
        entity: Dict[str, Any],
        relationships: List[Dict[str, Any]]
    ) -> str:
        """Format entity and relationships as readable text for LLM.

        Creates a natural language description of the entity and its
        connected relationships for inclusion in retrieval context.

        Args:
            entity: Entity dict with name, description, type
            relationships: List of relationship dicts with source, target, type, context

        Returns:
            Formatted context string with entity and relationship information
        """
        # Start with entity description
        parts = [f"{entity['name']}: {entity.get('description', 'No description available')}."]

        if relationships:
            # Group relationships by type
            depends_on = []
            configures = []
            connects_to = []
            is_part_of = []

            for rel in relationships:
                rel_type = rel.get('type', '')
                context = rel.get('context', '')

                # Determine if entity is source or target
                if rel.get('source') == entity['name']:
                    other = rel.get('target', '')
                    if rel_type == 'depends_on':
                        depends_on.append(f"{other} ({context})")
                    elif rel_type == 'configures':
                        configures.append(f"{other} ({context})")
                    elif rel_type == 'connects_to':
                        connects_to.append(f"{other} ({context})")
                    elif rel_type == 'is_part_of':
                        is_part_of.append(f"{other} ({context})")
                elif rel.get('target') == entity['name']:
                    other = rel.get('source', '')
                    # Reverse relationship semantics for incoming edges
                    if rel_type == 'depends_on':
                        parts.append(f"Required by: {other} ({context})")
                    elif rel_type == 'configures':
                        parts.append(f"Configured by: {other} ({context})")
                    elif rel_type == 'connects_to':
                        connects_to.append(f"{other} ({context})")  # Bidirectional
                    elif rel_type == 'is_part_of':
                        parts.append(f"Contains: {other} ({context})")

            # Add outgoing relationships
            if depends_on:
                parts.append(f"Depends on: {', '.join(depends_on)}.")
            if configures:
                parts.append(f"Configures: {', '.join(configures)}.")
            if connects_to:
                parts.append(f"Connects to: {', '.join(connects_to)}.")
            if is_part_of:
                parts.append(f"Is part of: {', '.join(is_part_of)}.")

        return " ".join(parts)

    async def retrieve_graph_context(
        self,
        query: str,
        user_id: str,
        request_id: str
    ) -> List[Dict[str, Any]]:
        """Retrieve graph-derived context for query.

        Extracts entities from query, expands via graph traversal, and
        returns context entries in chunk-like format for merging with
        semantic search results.

        Args:
            query: User's question
            user_id: User ID for graph isolation
            request_id: Request correlation ID

        Returns:
            List of graph-derived context dicts with chunk-like structure
        """
        start_time = time.time()

        # Extract entities from query
        entity_names = await self.extract_query_entities(query)

        if not entity_names:
            logger.info("no_query_entities",
                       request_id=request_id,
                       query=query[:100])
            return []

        # Determine traversal depth based on query type
        depth = 2 if self.is_relationship_query(query) else 1

        logger.info("graph_retrieval_started",
                   request_id=request_id,
                   user_id=user_id,
                   entity_count=len(entity_names),
                   depth=depth)

        # Retrieve subgraphs for top 3 entities (avoid explosion)
        graph_contexts = []
        top_entities = entity_names[:3]

        for entity_name in top_entities:
            try:
                # Get subgraph for this entity
                subgraph = self.graph_store.get_subgraph(
                    entity_name=entity_name,
                    user_id=user_id,
                    depth=depth
                )

                nodes = subgraph.get("nodes", [])
                edges = subgraph.get("edges", [])

                if not nodes:
                    continue

                # Convert subgraph to chunk-like entries
                # Primary entity gets its own entry
                for node in nodes:
                    # Find relationships for this node
                    node_relationships = [
                        edge for edge in edges
                        if edge.get("source") == node["name"] or edge.get("target") == node["name"]
                    ]

                    # Format as natural language context
                    formatted_text = self.format_relationship_context(node, node_relationships)

                    # Create chunk-like dict for merging
                    graph_chunk = {
                        "text": formatted_text,
                        "doc_id": node.get("doc_id", "graph"),
                        "chunk_id": f"graph-{node['name']}",
                        "filename": "Knowledge Graph",  # Distinguish from documents
                        "page_range": "N/A",
                        "source": "graph",  # Flag for citation tracking
                        "entity_name": node["name"],
                        "relationships": node_relationships,
                        "score": 0.9  # High score for entity matches
                    }

                    graph_contexts.append(graph_chunk)

            except Exception as e:
                logger.warning("entity_subgraph_failed",
                             request_id=request_id,
                             entity=entity_name,
                             error=str(e))
                continue

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info("graph_retrieval_complete",
                   request_id=request_id,
                   entity_count=len(top_entities),
                   graph_chunk_count=len(graph_contexts),
                   latency_ms=latency_ms)

        return graph_contexts
