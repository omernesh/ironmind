"""Answer generation service using OpenAI GPT-5-mini."""
import time
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.models.chat import Citation
from app.core.logging import get_logger

logger = get_logger()


# System prompt for technical documentation assistant
SYSTEM_PROMPT = """You are a technical documentation assistant for aerospace/defense systems.
Answer questions using ONLY the provided document excerpts and knowledge graph information.
Include citation numbers [1], [2], etc. for each claim you make.
If information is not in the documents, say "Based on the available documents, I cannot find information about X."
Use concise, technical language (2-4 sentences).
When sources conflict, acknowledge the disagreement with citations.
Use Markdown for code snippets, formulas, or structured data.

When citing knowledge graph information, note that these are system-inferred relationships based on extracted entities. Mark such citations clearly."""


class Generator:
    """
    Answer generation using OpenAI GPT-5-mini.

    Builds grounded prompts from retrieved chunks and generates
    answers with inline citations.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    async def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        request_id: str,
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate answer from retrieved chunks.

        Args:
            query: User's question
            chunks: Reranked chunks with metadata
            request_id: Request correlation ID
            history: Optional conversation history

        Returns:
            {
                "answer": Generated answer text,
                "citations": List of Citation objects,
                "latency_ms": Generation time in ms,
                "tokens_used": Token count for diagnostics
            }
        """
        start_time = time.time()

        # Handle empty/low context
        if not chunks:
            logger.warning(
                "no_chunks_for_generation",
                request_id=request_id,
                query=query[:100]
            )
            return {
                "answer": "I cannot find relevant information in the uploaded documents.",
                "citations": [],
                "latency_ms": int((time.time() - start_time) * 1000),
                "tokens_used": 0
            }

        # Build context from chunks
        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            # Distinguish graph-derived context from document chunks
            if chunk.get('source') == 'graph':
                entity_name = chunk.get('entity_name', 'Unknown')
                citation_header = f"[{idx}: Knowledge Graph - {entity_name}]"
            else:
                citation_header = f"[{idx}: {chunk['filename']}, p.{chunk['page_range']}]"

            context_parts.append(f"{citation_header}\n{chunk['text']}\n")
        context = "\n".join(context_parts)

        # Build user prompt
        user_prompt = f"""Context:
{context}

Question: {query}

Answer the question using only the context above. Include citation numbers [1], [2], etc."""

        # Build messages list
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Include conversation history if provided (keep last 5 turns)
        if history:
            recent_history = history[-10:]  # Last 5 turns = 10 messages (user + assistant pairs)
            messages.extend(recent_history)

        # Add current query
        messages.append({"role": "user", "content": user_prompt})

        # Call OpenAI API
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=30.0
            )

            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Build Citation objects
            citations = []
            for idx, chunk in enumerate(chunks, 1):
                snippet = chunk['text'][:200]
                if len(chunk['text']) > 200:
                    snippet += "..."

                # Determine source type
                source_type = chunk.get('source', 'document')

                citation = Citation(
                    id=idx,
                    doc_id=chunk['doc_id'],
                    filename=chunk['filename'],
                    page_range=chunk['page_range'],
                    section_title=chunk.get('section_title'),
                    snippet=snippet,
                    score=chunk.get('rerank_score', chunk.get('score')),
                    source=source_type  # 'document' or 'graph'
                )
                citations.append(citation)

            latency_ms = int((time.time() - start_time) * 1000)

            # Log diagnostics
            logger.info(
                "answer_generated",
                request_id=request_id,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                chunks_used=len(chunks),
                answer_length=len(answer)
            )

            return {
                "answer": answer,
                "citations": citations,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used
            }

        except Exception as e:
            logger.error(
                "generation_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Re-raise with user-friendly message
            raise Exception(f"Failed to generate answer: {str(e)}") from e
