"""Pydantic schemas for knowledge graph entities and relationships.

These schemas enforce type constraints for entity extraction using
OpenAI Structured Outputs, ensuring 100% schema compliance.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Entity extracted from technical aerospace/defense documentation.

    Attributes:
        name: Entity name (e.g., "GPS Module", "Flight Controller API")
        type: Entity category - strictly one of:
            - hardware: Physical systems, subsystems, modules, sensors, actuators
            - software: APIs, services, protocols, interfaces, algorithms
            - configuration: Settings, thresholds, modes, flags, parameters
            - error: Error codes, fault conditions, failure scenarios
        description: Brief description extracted from document context
        parent_entity: Optional parent entity name for hierarchical extraction
            (e.g., "GPS Module" has parent_entity="Navigation System")
        doc_id: Source document identifier for traceability
        chunk_id: Source chunk identifier for provenance tracking
    """
    name: str = Field(
        ...,
        description="Entity name as it appears in documentation",
        examples=["GPS Module", "Autonomous Navigation System", "CALIBRATE_IMU"]
    )
    type: Literal["hardware", "software", "configuration", "error"] = Field(
        ...,
        description="Entity category based on aerospace domain taxonomy"
    )
    description: str = Field(
        ...,
        description="Brief description of entity's purpose or function",
        examples=[
            "Global Positioning System receiver module for location tracking",
            "Configuration parameter controlling sensor update frequency"
        ]
    )
    parent_entity: Optional[str] = Field(
        default=None,
        description="Parent entity name for hierarchical relationships (is_part_of)"
    )
    doc_id: str = Field(
        ...,
        description="Source document identifier"
    )
    chunk_id: str = Field(
        ...,
        description="Source chunk identifier for citation traceability"
    )


class Relationship(BaseModel):
    """Relationship between two entities in the knowledge graph.

    Attributes:
        source_entity: Name of the source entity (must match Entity.name)
        target_entity: Name of the target entity (must match Entity.name)
        relationship_type: Relationship category - strictly one of:
            - depends_on: Source requires target to function correctly
            - configures: Source sets parameters or controls target behavior
            - connects_to: Source interfaces or communicates with target
            - is_part_of: Source is a component/subsystem of target (hierarchy)
        context: Sentence from documentation describing the relationship.
            Used for LLM grounding and relationship provenance.
        doc_id: Source document identifier where relationship was found
    """
    source_entity: str = Field(
        ...,
        description="Name of source entity in relationship"
    )
    target_entity: str = Field(
        ...,
        description="Name of target entity in relationship"
    )
    relationship_type: Literal["depends_on", "configures", "connects_to", "is_part_of"] = Field(
        ...,
        description="Relationship category based on technical documentation patterns"
    )
    context: str = Field(
        ...,
        description="Sentence from document describing this relationship",
        examples=[
            "The Navigation System requires GPS Module for position tracking.",
            "Flight Controller configures the IMU sampling rate via API."
        ]
    )
    doc_id: str = Field(
        ...,
        description="Source document identifier"
    )


class GraphExtraction(BaseModel):
    """Complete graph extraction result from a document chunk.

    This schema is used with OpenAI Structured Outputs to guarantee
    100% schema compliance during entity/relationship extraction.

    Attributes:
        entities: List of entities extracted from chunk
        relationships: List of relationships between extracted entities
    """
    entities: List[Entity] = Field(
        default_factory=list,
        description="Entities extracted from document chunk"
    )
    relationships: List[Relationship] = Field(
        default_factory=list,
        description="Relationships between entities found in chunk"
    )
