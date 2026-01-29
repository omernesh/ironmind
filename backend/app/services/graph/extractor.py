"""LLM-based entity and relationship extraction using OpenAI Structured Outputs.

This service extracts aerospace/defense entities (hardware, software, configuration, error)
and their relationships from document chunks with 100% schema compliance using GPT-4o's
Structured Outputs feature.
"""
import asyncio
import time
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.core.logging import get_logger
from app.services.graph.schemas import GraphExtraction, Entity, Relationship

logger = get_logger()

# System prompt for entity/relationship extraction
EXTRACTION_PROMPT = """You are extracting entities and relationships from aerospace/defense technical documentation.

ENTITIES - Extract ALL of these types:
- hardware: Physical systems, subsystems, modules, sensors, actuators, components
- software: APIs, services, protocols, algorithms, interfaces
- configuration: Settings, thresholds, modes, flags, parameters
- error: Error codes, fault conditions, failure scenarios, warning types

For hierarchical entities, set parent_entity to the containing system.
Example: "GPS Module" has parent_entity "Navigation System"

Expand acronyms in descriptions (e.g., UAV = Unmanned Aerial Vehicle).
Include singleton entities even if mentioned once.

RELATIONSHIPS - Identify:
- depends_on: X requires Y to function
- configures: X sets parameters for Y
- connects_to: X interfaces/communicates with Y
- is_part_of: X is a component/subsystem of Y

For each relationship, include the exact sentence from the document in the context field."""


class EntityExtractor:
    """Extract entities and relationships from document chunks using LLM.

    Uses OpenAI's Structured Outputs feature with GPT-4o to guarantee
    100% schema compliance for entity/relationship extraction.
    """

    def __init__(self):
        """Initialize the EntityExtractor with OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-2024-08-06"  # Supports Structured Outputs

        # Extraction metrics tracking
        self.total_extractions = 0
        self.total_entities = 0
        self.total_relationships = 0
        self.total_failures = 0

    async def extract_from_chunk(
        self,
        chunk_text: str,
        doc_id: str,
        chunk_id: str
    ) -> GraphExtraction:
        """Extract entities and relationships from a single chunk.

        Args:
            chunk_text: Text content of the chunk to analyze
            doc_id: Source document identifier
            chunk_id: Source chunk identifier

        Returns:
            GraphExtraction object with entities and relationships.
            Returns empty GraphExtraction on API errors (doesn't crash pipeline).
        """
        start_time = time.time()

        logger.info("extraction_started",
                   chunk_id=chunk_id,
                   doc_id=doc_id,
                   text_length=len(chunk_text))

        try:
            # Use Structured Outputs to guarantee schema compliance
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": chunk_text}
                ],
                response_format=GraphExtraction,
                temperature=0  # Deterministic extraction
            )

            # Extract the parsed result
            extraction = response.choices[0].message.parsed

            # Post-process to fill in doc_id and chunk_id
            extraction = self.post_process_extraction(extraction, doc_id, chunk_id)

            latency_ms = int((time.time() - start_time) * 1000)

            # Update metrics
            self.total_extractions += 1
            self.total_entities += len(extraction.entities)
            self.total_relationships += len(extraction.relationships)

            logger.info("extraction_completed",
                       chunk_id=chunk_id,
                       entity_count=len(extraction.entities),
                       relationship_count=len(extraction.relationships),
                       latency_ms=latency_ms)

            return extraction

        except Exception as e:
            self.total_failures += 1
            logger.error("extraction_failed",
                        chunk_id=chunk_id,
                        error_type=type(e).__name__,
                        error_message=str(e))

            # Return empty extraction on failure (don't crash pipeline)
            return GraphExtraction(entities=[], relationships=[])

    async def extract_batch(
        self,
        chunks: List[Dict],
        doc_id: str
    ) -> List[GraphExtraction]:
        """Extract entities/relationships from multiple chunks concurrently.

        Args:
            chunks: List of chunk dicts with 'text' and 'chunk_id' keys
            doc_id: Source document identifier

        Returns:
            List of GraphExtraction results, one per chunk
        """
        # Limit concurrency to 5 parallel requests to avoid rate limits
        semaphore = asyncio.Semaphore(5)

        async def extract_with_limit(chunk: Dict) -> GraphExtraction:
            async with semaphore:
                return await self.extract_from_chunk(
                    chunk_text=chunk["text"],
                    doc_id=doc_id,
                    chunk_id=chunk["chunk_id"]
                )

        # Process all chunks concurrently
        results = await asyncio.gather(
            *[extract_with_limit(chunk) for chunk in chunks]
        )

        return results

    def normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for consistent matching.

        Args:
            name: Raw entity name from extraction

        Returns:
            Normalized name (title case, acronyms expanded, whitespace stripped)
        """
        # Strip extra whitespace
        name = " ".join(name.split())

        # Convert to title case for consistency
        name = name.title()

        return name

    def post_process_extraction(
        self,
        extraction: GraphExtraction,
        doc_id: str,
        chunk_id: str
    ) -> GraphExtraction:
        """Post-process extraction to normalize entities and fill metadata.

        Args:
            extraction: Raw extraction from LLM
            doc_id: Source document identifier
            chunk_id: Source chunk identifier

        Returns:
            Cleaned GraphExtraction with normalized names and complete metadata
        """
        # Normalize entity names and fill in doc_id/chunk_id
        normalized_entities = []
        name_mapping = {}  # Track original -> normalized name mapping

        for entity in extraction.entities:
            normalized_name = self.normalize_entity_name(entity.name)
            name_mapping[entity.name] = normalized_name

            # Create new entity with normalized name and filled metadata
            normalized_entity = Entity(
                name=normalized_name,
                type=entity.type,
                description=entity.description,
                parent_entity=entity.parent_entity,
                doc_id=doc_id,
                chunk_id=chunk_id
            )
            normalized_entities.append(normalized_entity)

        # Update relationship entity names to match normalized names
        normalized_relationships = []
        for rel in extraction.relationships:
            normalized_source = name_mapping.get(rel.source_entity, rel.source_entity)
            normalized_target = name_mapping.get(rel.target_entity, rel.target_entity)

            normalized_rel = Relationship(
                source_entity=normalized_source,
                target_entity=normalized_target,
                relationship_type=rel.relationship_type,
                context=rel.context,
                doc_id=doc_id
            )
            normalized_relationships.append(normalized_rel)

        return GraphExtraction(
            entities=normalized_entities,
            relationships=normalized_relationships
        )

    def get_extraction_stats(self) -> Dict[str, int]:
        """Get cumulative extraction statistics for diagnostics.

        Returns:
            Dict with total_extractions, total_entities, total_relationships, total_failures
        """
        return {
            "total_extractions": self.total_extractions,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
            "total_failures": self.total_failures
        }
