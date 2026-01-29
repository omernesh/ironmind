"""Debug endpoints for graph inspection and troubleshooting.

Provides endpoints to examine knowledge graph contents, statistics,
and subgraph visualization data.
"""
from typing import Literal, Optional, Dict, List, Any
from fastapi import APIRouter, Depends, Query
import structlog

from app.middleware.auth import get_current_user_id
from app.services.graph.graph_store import GraphStore

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


def format_edgelist(subgraph: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Format subgraph as simple edge list.

    Args:
        subgraph: Dict with "nodes" and "edges" lists

    Returns:
        Dict with simplified edge list and node count
    """
    edges = []
    for edge in subgraph.get("edges", []):
        edges.append({
            "from": edge.get("source"),
            "to": edge.get("target"),
            "relationship": edge.get("type", "unknown"),
            "context": edge.get("context", "")
        })

    return {
        "nodes": len(subgraph.get("nodes", [])),
        "edges": edges,
        "node_details": subgraph.get("nodes", [])
    }


def format_cytoscape(subgraph: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Format subgraph as Cytoscape.js elements.

    Args:
        subgraph: Dict with "nodes" and "edges" lists

    Returns:
        Dict with Cytoscape.js format: {"elements": {"nodes": [...], "edges": [...]}}
    """
    nodes = []
    for node in subgraph.get("nodes", []):
        nodes.append({
            "data": {
                "id": node.get("name"),
                "label": node.get("name"),
                "type": node.get("type", "unknown"),
                "description": node.get("description", "")
            }
        })

    edges = []
    edge_id = 0
    for edge in subgraph.get("edges", []):
        edge_id += 1
        edges.append({
            "data": {
                "id": f"edge_{edge_id}",
                "source": edge.get("source"),
                "target": edge.get("target"),
                "label": edge.get("type", "unknown"),
                "context": edge.get("context", "")
            }
        })

    return {
        "elements": {
            "nodes": nodes,
            "edges": edges
        }
    }


@router.get("/graph/sample")
async def get_graph_sample(
    entity: str = Query(..., description="Entity name to center subgraph on"),
    format: Literal["edgelist", "cytoscape"] = Query(
        "edgelist",
        description="Output format: edgelist or cytoscape"
    ),
    depth: int = Query(2, ge=1, le=3, description="Traversal depth"),
    user_id: str = Depends(get_current_user_id)
):
    """Return subgraph centered on specified entity.

    Used for debugging graph population and retrieval.

    Formats:
    - edgelist: Simple JSON with nodes array and edges array
    - cytoscape: Cytoscape.js format for visualization

    Args:
        entity: Entity name to start traversal from
        format: Output format (edgelist or cytoscape)
        depth: Maximum traversal depth (1-3 hops)
        user_id: Current user ID (from auth)

    Returns:
        Subgraph data in requested format
    """
    logger.info(
        "graph_sample_requested",
        entity=entity,
        format=format,
        depth=depth,
        user_id=user_id
    )

    graph_store = GraphStore()
    subgraph = graph_store.get_subgraph(entity, user_id, depth)

    if format == "cytoscape":
        result = format_cytoscape(subgraph)
    else:
        result = format_edgelist(subgraph)

    logger.info(
        "graph_sample_returned",
        entity=entity,
        nodes_count=len(subgraph.get("nodes", [])),
        edges_count=len(subgraph.get("edges", [])),
        format=format
    )

    return result


@router.get("/graph/stats")
async def get_graph_stats(user_id: str = Depends(get_current_user_id)):
    """Return graph statistics for current user.

    Provides counts of entities, relationships, and breakdown by entity type.

    Args:
        user_id: Current user ID (from auth)

    Returns:
        Dict with entity_count, relationship_count, and entity_types
    """
    logger.info("graph_stats_requested", user_id=user_id)

    graph_store = GraphStore()

    stats = {
        "entity_count": graph_store.count_entities(user_id),
        "relationship_count": graph_store.count_relationships(user_id),
        "entity_types": graph_store.get_entity_type_counts(user_id)
    }

    logger.info(
        "graph_stats_returned",
        entity_count=stats["entity_count"],
        relationship_count=stats["relationship_count"],
        user_id=user_id
    )

    return stats
