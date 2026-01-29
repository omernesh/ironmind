"""Hybrid retrieval service for RAG pipeline."""
import time
from typing import List, Dict, Any, Optional
from app.services.indexer import TxtaiIndexer
from app.services.graph.graph_retriever import GraphRetriever
from app.services.graph.doc_relationships import DocumentRelationshipStore
from app.config import settings
from app.core.logging import get_logger

logger = get_logger()

# Aerospace/defense domain acronyms for query expansion
ACRONYM_MAP = {
    "UAV": "Unmanned Aerial Vehicle",
    "IMU": "Inertial Measurement Unit",
    "GPS": "Global Positioning System",
    "INS": "Inertial Navigation System",
    "GNSS": "Global Navigation Satellite System",
    "RADAR": "Radio Detection and Ranging",
    "LIDAR": "Light Detection and Ranging",
    "EO": "Electro-Optical",
    "IR": "Infrared",
    "RF": "Radio Frequency",
    "C2": "Command and Control",
    "ISR": "Intelligence Surveillance Reconnaissance",
    "SATCOM": "Satellite Communications",
    "MTBF": "Mean Time Between Failures",
    "SWaP": "Size Weight and Power",
}


def preprocess_query(query: str) -> str:
    """
    Preprocess query with acronym expansion.

    Expands common aerospace/defense acronyms to improve semantic search.
    """
    import re

    def expand_acronym(match):
        acronym = match.group(0)
        if acronym in ACRONYM_MAP:
            return f"{acronym} ({ACRONYM_MAP[acronym]})"
        return acronym

    # Find uppercase acronyms (2+ letters)
    expanded = re.sub(r'\b[A-Z]{2,}\b', expand_acronym, query)
    return expanded.strip()


class HybridRetriever:
    """
    Hybrid retrieval combining semantic and BM25 search.

    Wraps TxtaiIndexer.hybrid_search() with query preprocessing,
    diagnostics logging, and structured response format.
    """

    def __init__(
        self,
        indexer: Optional[TxtaiIndexer] = None,
        graph_retriever: Optional[GraphRetriever] = None,
        doc_rel_store: Optional[DocumentRelationshipStore] = None
    ):
        self.indexer = indexer or TxtaiIndexer()
        self.graph_retriever = graph_retriever or GraphRetriever()
        self.doc_rel_store = doc_rel_store or DocumentRelationshipStore()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        request_id: str,
        limit: int = None,
        weights: float = None,
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks using hybrid search.

        Args:
            query: User's question
            user_id: User ID for filtering
            request_id: Request correlation ID
            limit: Override default retrieval limit
            weights: Override default hybrid weights
            threshold: Override default relevance threshold

        Returns:
            {
                "chunks": List of chunk dicts with metadata,
                "count": Number of chunks returned,
                "latency_ms": Retrieval time in ms,
                "diagnostics": {
                    "query_original": Original query,
                    "query_expanded": Query after acronym expansion,
                    "score_min": Minimum score in results,
                    "score_max": Maximum score in results,
                    "score_avg": Average score
                }
            }
        """
        start_time = time.time()

        # Apply defaults from settings
        limit = limit or settings.RETRIEVAL_LIMIT
        weights = weights if weights is not None else settings.HYBRID_WEIGHT
        threshold = threshold if threshold is not None else settings.RELEVANCE_THRESHOLD

        # Preprocess query with acronym expansion
        expanded_query = preprocess_query(query)

        logger.info("retrieval_started",
                   request_id=request_id,
                   user_id=user_id,
                   query_length=len(query),
                   expanded=expanded_query != query)

        # Channel 1: Semantic + BM25 hybrid search
        semantic_chunks = self.indexer.hybrid_search(
            query=expanded_query,
            user_id=user_id,
            limit=limit,
            weights=weights,
            threshold=threshold
        )

        # Channel 2: Graph context (if enabled)
        graph_chunks = []
        graph_latency_ms = 0
        graph_entity_count = 0
        graph_enabled = getattr(settings, 'GRAPH_RETRIEVAL_ENABLED', True)

        if graph_enabled:
            graph_start = time.time()
            try:
                graph_chunks = await self.graph_retriever.retrieve_graph_context(
                    query=query,
                    user_id=user_id,
                    request_id=request_id
                )
                graph_latency_ms = int((time.time() - graph_start) * 1000)

                # Extract entity count from graph chunks
                unique_entities = set(c.get("entity_name") for c in graph_chunks if c.get("entity_name"))
                graph_entity_count = len(unique_entities)

                logger.info("graph_retrieval_complete",
                           request_id=request_id,
                           graph_chunk_count=len(graph_chunks),
                           entity_count=graph_entity_count,
                           latency_ms=graph_latency_ms)
            except Exception as e:
                logger.warning("graph_retrieval_failed",
                             request_id=request_id,
                             error=str(e))
                # Continue without graph context

        # Merge channels
        merged_chunks = self._merge_channels(semantic_chunks, graph_chunks)

        # Expand with related documents (for multi-source synthesis)
        doc_expansion_enabled = getattr(settings, 'DOC_RELATIONSHIP_EXPANSION_ENABLED', True)
        if doc_expansion_enabled and len(merged_chunks) > 0:
            try:
                # Get doc IDs from current results
                current_doc_ids = list(set(
                    c.get('doc_id') for c in merged_chunks
                    if c.get('doc_id') and c.get('source') != 'graph'
                ))

                if len(current_doc_ids) >= 1:
                    # Find related documents
                    related_docs = self.doc_rel_store.get_related_documents(
                        doc_ids=current_doc_ids,
                        user_id=user_id,
                        min_strength=0.5
                    )

                    # Get IDs of docs not already in results
                    new_doc_ids = [
                        d['doc_id'] for d in related_docs
                        if d['doc_id'] not in current_doc_ids
                    ][:2]  # Limit expansion to 2 related docs

                    if new_doc_ids:
                        # Fetch chunks from related docs
                        for related_doc_id in new_doc_ids:
                            related_chunks = self.indexer.hybrid_search(
                                query=expanded_query,
                                user_id=user_id,
                                limit=3,  # Fewer chunks per related doc
                                weights=weights,
                                threshold=threshold
                            )

                            # Filter to only chunks from the related doc and add if not already present
                            for chunk in related_chunks:
                                if chunk.get('doc_id') == related_doc_id and chunk not in merged_chunks:
                                    # Mark as expanded
                                    chunk['expanded_from_relationship'] = True
                                    merged_chunks.append(chunk)

                        logger.info(
                            "doc_relationship_expansion_complete",
                            request_id=request_id,
                            original_docs=len(current_doc_ids),
                            expanded_docs=len(new_doc_ids),
                            total_chunks=len(merged_chunks)
                        )

            except Exception as e:
                logger.warning("doc_relationship_expansion_failed",
                              request_id=request_id,
                              error=str(e))

        latency_ms = int((time.time() - start_time) * 1000)

        # Calculate score statistics for diagnostics
        scores = [c.get("score", 0) for c in merged_chunks]
        diagnostics = {
            "query_original": query,
            "query_expanded": expanded_query,
            "score_min": min(scores) if scores else 0,
            "score_max": max(scores) if scores else 0,
            "score_avg": sum(scores) / len(scores) if scores else 0,
            "graph_entity_count": graph_entity_count,
            "graph_context_count": len(graph_chunks),
            "graph_latency_ms": graph_latency_ms
        }

        logger.info("retrieval_complete",
                   request_id=request_id,
                   count=len(merged_chunks),
                   semantic_count=len(semantic_chunks),
                   graph_count=len(graph_chunks),
                   latency_ms=latency_ms,
                   score_range=f"{diagnostics['score_min']:.3f}-{diagnostics['score_max']:.3f}")

        return {
            "chunks": merged_chunks,
            "count": len(merged_chunks),
            "latency_ms": latency_ms,
            "diagnostics": diagnostics
        }

    def _merge_channels(
        self,
        semantic: List[Dict[str, Any]],
        graph: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge semantic search and graph context channels.

        Priority: semantic chunks first (higher confidence from hybrid search).
        Deduplication: Skip graph chunks if entity already covered in semantic text.

        Args:
            semantic: Chunks from hybrid search (semantic + BM25)
            graph: Chunks from graph retrieval (entity subgraphs)

        Returns:
            Merged list with semantic chunks + unique graph context
        """
        # Start with semantic chunks (higher confidence)
        merged = list(semantic)

        # Track entity names mentioned in semantic chunks
        semantic_text = " ".join(c.get("text", "") for c in semantic).lower()

        # Add graph chunks that provide NEW entity information
        for graph_chunk in graph:
            entity_name = graph_chunk.get("entity_name", "")

            # Skip if entity already covered in semantic chunks
            if entity_name.lower() in semantic_text:
                continue

            # Add unique graph context
            merged.append(graph_chunk)

            # Maintain limit (don't exceed 2x original limit)
            if len(merged) >= len(semantic) * 2:
                break

        return merged
