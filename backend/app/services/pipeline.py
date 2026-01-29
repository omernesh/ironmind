"""Document processing pipeline orchestration."""
import time
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.core.database import DocumentDatabase
from app.services.docling_client import DoclingClient, DoclingError
from app.services.chunker import SemanticChunker
from app.services.indexer import TxtaiIndexer
from app.services.storage import StorageService
from app.services.graph import EntityExtractor, GraphStore, DocumentRelationshipStore, CrossReferenceDetector
from app.models.documents import ProcessingStatus, ProcessingLogEntry
from app.config import settings

logger = get_logger()


class DocumentPipeline:
    """
    Orchestrates document processing: parse -> chunk -> index.

    Updates document status at each stage and logs processing events.
    """

    def __init__(self):
        self.db = DocumentDatabase(settings.database_path)
        self.docling = DoclingClient()
        self.chunker = SemanticChunker()
        self.indexer = TxtaiIndexer()
        self.storage = StorageService(settings.DATA_DIR)
        self.extractor = EntityExtractor()
        self.graph_store = GraphStore()
        self.doc_rel_store = DocumentRelationshipStore()
        self.cross_ref_detector = CrossReferenceDetector()

    async def process_document(
        self,
        doc_id: str,
        user_id: str,
        file_path: Path
    ) -> bool:
        """
        Process document through complete pipeline.

        Stages:
        1. PARSING - Call docling-serve to extract structure
        2. CHUNKING - Apply semantic chunking
        3. INDEXING - Store in txtai
        4. DONE - Complete

        Returns True if successful, False if failed.
        """
        pipeline_start = time.time()
        processing_log = []

        logger.info("doc_ingestion_started",
                   doc_id=doc_id,
                   user_id=user_id,
                   file_path=str(file_path))

        try:
            # Stage 1: PARSING
            stage_start = time.time()
            await self._update_status(doc_id, user_id, ProcessingStatus.PARSING, "Parsing document with docling")

            parse_result = await self.docling.parse_document(file_path)

            # Save parsed output
            await self.storage.save_processed_json(user_id, doc_id, parse_result)

            processing_log.append(ProcessingLogEntry(
                stage="Parsing",
                started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_ms=int((time.time() - stage_start) * 1000)
            ))

            # Extract page count if available
            page_count = parse_result.get("page_count", len(parse_result.get("pages", [])))

            # Stage 2: CHUNKING
            stage_start = time.time()
            await self._update_status(doc_id, user_id, ProcessingStatus.CHUNKING, "Creating semantic chunks")

            doc = await self.db.get_document(doc_id)
            chunks = self.chunker.chunk_document(
                parse_result,
                doc_id,
                user_id,
                doc.filename
            )

            processing_log.append(ProcessingLogEntry(
                stage="Chunking",
                started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_ms=int((time.time() - stage_start) * 1000)
            ))

            # Stage 3: GRAPH EXTRACTION
            stage_start = time.time()
            entity_count = 0
            relationship_count = 0

            try:
                await self._update_status(doc_id, user_id, ProcessingStatus.GRAPH_EXTRACTING, "Extracting entities for knowledge graph")

                # Clear any existing graph data for this document (for re-ingestion)
                self.graph_store.delete_document_entities(doc_id, user_id)

                # Extract from each chunk
                for chunk in chunks:
                    extraction = await self.extractor.extract_from_chunk(
                        chunk_text=chunk.text,
                        doc_id=doc_id,
                        chunk_id=chunk.chunk_id
                    )

                    # Store entities
                    for entity in extraction.entities:
                        self.graph_store.add_entity(entity, user_id)
                        entity_count += 1

                    # Store relationships
                    for rel in extraction.relationships:
                        self.graph_store.add_relationship(rel, user_id)
                        relationship_count += 1

                processing_log.append(ProcessingLogEntry(
                    stage="GraphExtracting",
                    started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=int((time.time() - stage_start) * 1000)
                ))

                logger.info("graph_extraction_completed",
                           doc_id=doc_id,
                           entity_count=entity_count,
                           relationship_count=relationship_count)

            except Exception as e:
                # Log warning but continue to indexing (graph is enhancement, not critical path)
                logger.warning("graph_extraction_failed",
                              doc_id=doc_id,
                              error=str(e))
                processing_log.append(ProcessingLogEntry(
                    stage="GraphExtracting",
                    started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=int((time.time() - stage_start) * 1000),
                    error=str(e)
                ))

            # Stage 3.5: DOCUMENT RELATIONSHIPS
            stage_start = time.time()
            doc_relationship_count = 0

            try:
                # Get list of existing documents for this user
                existing_docs = await self.db.list_user_documents(user_id)
                existing_doc_list = [
                    {"doc_id": d.doc_id, "filename": d.filename}
                    for d in existing_docs
                    if d.doc_id != doc_id and d.status == ProcessingStatus.DONE
                ]

                if existing_doc_list:
                    # Get full text for cross-reference detection
                    doc_text = parse_result.get("md_content", "")
                    if not doc_text:
                        # Fallback to concatenated sections
                        sections = parse_result.get("sections", [])
                        doc_text = "\n".join(s.get("content", "") for s in sections)

                    # Detect cross-references
                    relationships = await self.cross_ref_detector.detect_cross_references(
                        doc_id=doc_id,
                        doc_text=doc_text,
                        user_id=user_id,
                        existing_docs=existing_doc_list
                    )

                    # Add document node
                    self.doc_rel_store.add_document_node(
                        doc_id=doc_id,
                        filename=doc.filename,
                        user_id=user_id,
                        page_count=page_count,
                        chunk_count=len(chunks)
                    )

                    # Store relationships
                    for rel in relationships:
                        if self.doc_rel_store.add_relationship(rel, user_id):
                            doc_relationship_count += 1

                processing_log.append(ProcessingLogEntry(
                    stage="DocumentRelationships",
                    started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=int((time.time() - stage_start) * 1000)
                ))

                logger.info("document_relationships_extracted",
                           doc_id=doc_id,
                           relationship_count=doc_relationship_count)

            except Exception as e:
                # Log warning but continue (relationships are enhancement, not critical)
                logger.warning("document_relationship_extraction_failed",
                              doc_id=doc_id,
                              error=str(e))
                processing_log.append(ProcessingLogEntry(
                    stage="DocumentRelationships",
                    started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=int((time.time() - stage_start) * 1000),
                    error=str(e)
                ))

            # Stage 4: INDEXING
            stage_start = time.time()
            await self._update_status(doc_id, user_id, ProcessingStatus.INDEXING, "Indexing chunks in txtai")

            indexed_count = self.indexer.index_chunks(chunks, user_id, doc_id)

            processing_log.append(ProcessingLogEntry(
                stage="Indexing",
                started_at=datetime.fromtimestamp(stage_start, timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_ms=int((time.time() - stage_start) * 1000)
            ))

            # Stage 5: DONE
            total_duration_ms = int((time.time() - pipeline_start) * 1000)

            doc = await self.db.get_document(doc_id)
            doc.status = ProcessingStatus.DONE
            doc.current_stage = "Complete"
            doc.page_count = page_count
            doc.chunk_count = indexed_count
            doc.entity_count = entity_count
            doc.relationship_count = relationship_count
            doc.doc_relationship_count = doc_relationship_count
            doc.processing_log.extend(processing_log)
            await self.db.update_document(doc)

            logger.info("doc_ingestion_completed",
                       doc_id=doc_id,
                       user_id=user_id,
                       duration_ms=total_duration_ms,
                       page_count=page_count,
                       chunk_count=indexed_count)

            return True

        except DoclingError as e:
            await self._handle_failure(doc_id, user_id, f"Document parsing failed: {e}", processing_log)
            return False

        except Exception as e:
            logger.exception("pipeline_error", doc_id=doc_id, error=str(e))
            await self._handle_failure(doc_id, user_id, f"Processing error: {e}", processing_log)
            return False

    async def _update_status(
        self,
        doc_id: str,
        user_id: str,
        status: ProcessingStatus,
        current_stage: str
    ):
        """Update document status in database."""
        doc = await self.db.get_document(doc_id)
        if doc:
            doc.status = status
            doc.current_stage = current_stage
            await self.db.update_document(doc)

    async def _handle_failure(
        self,
        doc_id: str,
        user_id: str,
        error: str,
        processing_log: list
    ):
        """Handle pipeline failure."""
        logger.error("doc_ingestion_failed", doc_id=doc_id, error=error)

        doc = await self.db.get_document(doc_id)
        if doc:
            doc.status = ProcessingStatus.FAILED
            doc.current_stage = "Failed"
            doc.error = error
            doc.processing_log.extend(processing_log)
            await self.db.update_document(doc)

        # Clean up files on failure (per CONTEXT.md decision)
        try:
            self.storage.delete_document_files(user_id, doc_id)
        except Exception as e:
            logger.warning("cleanup_failed", doc_id=doc_id, error=str(e))


# Stage weights for progress estimation
STAGE_WEIGHTS = {
    "Uploading": 0.10,
    "Parsing": 0.30,
    "Chunking": 0.15,
    "GraphExtracting": 0.15,
    "DocumentRelationships": 0.05,
    "Indexing": 0.25,
    "Complete": 1.0
}


def calculate_progress(status: ProcessingStatus, current_stage: str) -> int:
    """Calculate progress percentage based on current stage."""
    if status == ProcessingStatus.DONE:
        return 100
    if status == ProcessingStatus.FAILED:
        return 0

    completed = 0.0
    for stage, weight in STAGE_WEIGHTS.items():
        if stage == current_stage:
            completed += weight * 0.5  # Assume halfway through current stage
            break
        completed += weight

    return min(99, int(completed * 100))


def estimate_time_remaining(
    current_stage: str,
    page_count: Optional[int] = None
) -> int:
    """
    Estimate seconds remaining based on stage and page count.

    Baseline: ~2 seconds per page (conservative estimate from RESEARCH.md)
    """
    if current_stage in ("Complete", "Failed"):
        return 0

    # Default to 30 pages if unknown
    pages = page_count or 30
    total_estimated = pages * 2  # 2 sec/page

    # Calculate remaining based on stage weights
    remaining_weight = 0.0
    found_stage = False
    for stage, weight in STAGE_WEIGHTS.items():
        if stage == current_stage:
            remaining_weight += weight * 0.5  # Half of current stage
            found_stage = True
        elif found_stage:
            remaining_weight += weight

    return max(0, int(total_estimated * remaining_weight))
