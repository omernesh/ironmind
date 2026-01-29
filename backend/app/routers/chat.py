"""Chat API endpoint with RAG pipeline."""
import time
import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.models.chat import ChatRequest, ChatResponse, DiagnosticInfo
from app.services.retriever import HybridRetriever
from app.services.reranker import Reranker
from app.services.generator import Generator
from app.middleware.auth import get_current_user_id
from app.core.logging import get_logger
from app.config import settings

router = APIRouter(prefix="/api", tags=["chat"])
logger = get_logger()

# Initialize services (singleton pattern)
retriever = HybridRetriever()
reranker = Reranker()
generator = Generator()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    RAG chat endpoint with hybrid retrieval, reranking, and generation.

    Three-stage pipeline:
    1. Hybrid Retrieval: semantic + BM25 search (25 chunks)
    2. Reranking: Cross-encoder scoring (top 12)
    3. Generation: GPT-5-mini with grounding (top 10)

    Performance target: <10 seconds (typical: 5-8s)
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info("chat_request_received",
                request_id=request_id,
                user_id=user_id,
                query_length=len(request.question))

    try:
        # Stage 1: Hybrid Retrieval
        retrieval_result = await retriever.retrieve(
            query=request.question,
            user_id=user_id,
            request_id=request_id
        )

        if retrieval_result["count"] == 0:
            # No relevant documents found
            return ChatResponse(
                answer="I couldn't find relevant information in your uploaded documents. Please try rephrasing your question or ensure relevant documents are uploaded.",
                citations=[],
                request_id=request_id,
                diagnostics=DiagnosticInfo(
                    retrieval_count=0,
                    rerank_count=0,
                    context_count=0,
                    retrieval_latency_ms=retrieval_result["latency_ms"],
                    rerank_latency_ms=0,
                    generation_latency_ms=0,
                    total_latency_ms=int((time.time() - start_time) * 1000)
                )
            )

        # Stage 2: Reranking
        rerank_result = await reranker.rerank(
            query=request.question,
            chunks=retrieval_result["chunks"],
            request_id=request_id
        )

        # Stage 3: Generation
        context_chunks = rerank_result["chunks"][:settings.CONTEXT_LIMIT]
        generation_result = await generator.generate(
            query=request.question,
            chunks=context_chunks,
            request_id=request_id,
            history=request.history
        )

        total_latency_ms = int((time.time() - start_time) * 1000)

        # Build diagnostic info
        diagnostics = DiagnosticInfo(
            retrieval_count=retrieval_result["count"],
            rerank_count=rerank_result["count"],
            context_count=len(context_chunks),
            retrieval_latency_ms=retrieval_result["latency_ms"],
            rerank_latency_ms=rerank_result["latency_ms"],
            generation_latency_ms=generation_result["latency_ms"],
            total_latency_ms=total_latency_ms
        )

        logger.info("chat_request_complete",
                    request_id=request_id,
                    total_latency_ms=total_latency_ms,
                    retrieval_count=retrieval_result["count"],
                    citations_count=len(generation_result["citations"]))

        return ChatResponse(
            answer=generation_result["answer"],
            citations=generation_result["citations"],
            request_id=request_id,
            diagnostics=diagnostics,
            synthesis_mode=generation_result.get("synthesis_mode", False),
            source_doc_count=generation_result.get("source_doc_count", 1)
        )

    except Exception as e:
        logger.error("chat_request_failed",
                     request_id=request_id,
                     error=str(e),
                     exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed. Request ID: {request_id}"
        )
