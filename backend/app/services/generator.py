"""Answer generation service using OpenAI GPT-5-mini."""
import time
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.models.chat import Citation
from app.core.logging import get_logger

logger = get_logger()

# Models requiring max_completion_tokens (GPT-5 and reasoning models)
REASONING_MODEL_PREFIXES = ('gpt-5', 'o1', 'o3', 'o4')


# System prompt for technical documentation assistant
SYSTEM_PROMPT = """You are a technical documentation assistant for aerospace/defense systems.
Answer questions using ONLY the provided document excerpts and knowledge graph information.
Include citation numbers [1], [2], etc. for each claim you make.
If information is not in the documents, say "Based on the available documents, I cannot find information about X."
Use concise, technical language (2-4 sentences).
When sources conflict, acknowledge the disagreement with citations.
Use Markdown for code snippets, formulas, or structured data.

When citing knowledge graph information, note that these are system-inferred relationships based on extracted entities. Mark such citations clearly."""


# Multi-source synthesis prompt (activated when 2+ documents in context)
SYNTHESIS_SYSTEM_PROMPT = """You are a technical documentation assistant synthesizing information from multiple aerospace/defense sources.

When answering from multiple documents:
1. ORGANIZE by subtopics - group related information together
2. INDICATE CONSENSUS - use phrases like "multiple sources mention", "consistently described as", "according to multiple documents"
3. HANDLE CONFLICTS - when sources disagree, cite both perspectives with their citations
4. USE COMPACT CITATIONS - for 3+ sources on same point, use notation like [1-3] instead of [1][2][3]
5. PRESERVE TRACEABILITY - every claim needs citation support

Answer structure for multi-document questions:
- Brief overview (1 sentence)
- Subtopic 1: [information from sources] [citations]
- Subtopic 2: [information from sources] [citations]
- If conflicts exist: Note disagreements with citations

Use concise technical language (2-5 sentences per subtopic).
When citing knowledge graph information, note these are system-inferred relationships."""


def should_activate_synthesis_mode(chunks: List[Dict[str, Any]]) -> bool:
    """
    Determine if multi-source synthesis mode should activate.

    Threshold: 2+ distinct documents in retrieved chunks, AND
    at least 2 chunks from each of 2 documents (avoid spurious triggers).
    """
    if not chunks:
        return False

    # Count chunks per document
    doc_chunk_counts = {}
    for chunk in chunks:
        doc_id = chunk.get('doc_id', '')
        # Skip graph-derived chunks for synthesis trigger
        if chunk.get('source') == 'graph':
            continue
        doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

    # Require 2+ documents with 2+ chunks each
    multi_chunk_docs = sum(1 for count in doc_chunk_counts.values() if count >= 2)
    return multi_chunk_docs >= 2


def build_synthesis_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Build context grouped by document for synthesis prompting.

    Groups chunks by source document to make cross-document patterns visible.
    """
    doc_groups = {}

    for idx, chunk in enumerate(chunks, 1):
        doc_id = chunk.get('doc_id', 'unknown')
        if doc_id not in doc_groups:
            doc_groups[doc_id] = {
                'filename': chunk.get('filename', 'Unknown'),
                'chunks': []
            }
        doc_groups[doc_id]['chunks'].append((idx, chunk))

    context_parts = []
    for doc_id, group in doc_groups.items():
        filename = group['filename']
        context_parts.append(f"\n=== {filename} ===")

        for idx, chunk in group['chunks']:
            page_range = chunk.get('page_range', '?')
            source_type = chunk.get('source', 'document')

            if source_type == 'graph':
                entity_name = chunk.get('entity_name', 'Unknown')
                header = f"[{idx}: Knowledge Graph - {entity_name}]"
            else:
                header = f"[{idx}: p.{page_range}]"

            context_parts.append(f"{header}\n{chunk.get('text', '')}\n")

    return "\n".join(context_parts)


class Generator:
    """
    Answer generation using OpenAI GPT-5-mini.

    Builds grounded prompts from retrieved chunks and generates
    answers with inline citations.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    def _is_reasoning_model(self, model: str) -> bool:
        """Check if model requires max_completion_tokens and omits temperature."""
        return model.lower().startswith(REASONING_MODEL_PREFIXES)

    def _build_completion_params(
        self,
        model: str,
        messages: list,
        max_tokens: int
    ) -> dict:
        """Build model-appropriate chat completion parameters.

        GPT-5 and o-series: use max_completion_tokens, omit temperature
        GPT-4 and older: use max_tokens with temperature
        """
        params = {
            'model': model,
            'messages': messages,
            'timeout': 30.0
        }

        if self._is_reasoning_model(model):
            params['max_completion_tokens'] = max_tokens
            # Note: temperature, top_p, presence_penalty, frequency_penalty
            # are not supported for reasoning models - intentionally omitted
        else:
            params['max_tokens'] = max_tokens
            params['temperature'] = self.temperature

        return params

    def _should_fallback(self, error: Exception) -> bool:
        """Check if error warrants falling back to GPT-4."""
        error_str = str(error).lower()
        # Fallback on model unavailability or unsupported parameter errors
        return any(keyword in error_str for keyword in [
            'model', 'unsupported', 'unavailable', 'does not exist'
        ])

    async def _call_completion(
        self,
        model: str,
        messages: list,
        max_tokens: int,
        request_id: str
    ) -> Any:
        """Make chat completion API call with model-aware parameters."""
        params = self._build_completion_params(model, messages, max_tokens)

        param_type = "max_completion_tokens" if self._is_reasoning_model(model) else "max_tokens"
        logger.debug("api_call_params",
                    model=model,
                    param_type=param_type,
                    max_tokens=max_tokens,
                    request_id=request_id)

        return await self.client.chat.completions.create(**params)

    async def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        request_id: str,
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate answer from retrieved chunks.

        Activates synthesis mode when chunks come from 2+ distinct documents.

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
                "tokens_used": Token count for diagnostics,
                "synthesis_mode": Whether multi-doc synthesis was used,
                "source_doc_count": Number of distinct source documents
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
                "tokens_used": 0,
                "synthesis_mode": False,
                "source_doc_count": 0
            }

        # Detect synthesis mode
        synthesis_mode = should_activate_synthesis_mode(chunks)
        unique_doc_ids = set(c.get('doc_id') for c in chunks if c.get('source') != 'graph')
        source_doc_count = len(unique_doc_ids)

        # Choose prompt and context format based on mode
        if synthesis_mode:
            system_prompt = SYNTHESIS_SYSTEM_PROMPT
            context = build_synthesis_context(chunks)
            user_prompt = f"""Context from {source_doc_count} documents:
{context}

Question: {query}

Think step-by-step:
1. What are the main subtopics relevant to this question?
2. What does each document say about each subtopic?
3. Where do documents agree? Where do they differ?
4. Synthesize a topic-organized answer with citations.

Answer:"""
            logger.info(
                "synthesis_mode_activated",
                request_id=request_id,
                source_doc_count=source_doc_count
            )
        else:
            system_prompt = SYSTEM_PROMPT
            # Standard context format
            context_parts = []
            for idx, chunk in enumerate(chunks, 1):
                if chunk.get('source') == 'graph':
                    entity_name = chunk.get('entity_name', 'Unknown')
                    citation_header = f"[{idx}: Knowledge Graph - {entity_name}]"
                else:
                    citation_header = f"[{idx}: {chunk['filename']}, p.{chunk['page_range']}]"
                context_parts.append(f"{citation_header}\n{chunk['text']}\n")
            context = "\n".join(context_parts)
            user_prompt = f"""Context:
{context}

Question: {query}

Answer the question using only the context above. Include citation numbers [1], [2], etc."""

        # Build messages list
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Include conversation history if provided (keep last 5 turns)
        if history:
            recent_history = history[-10:]
            messages.extend(recent_history)

        # Add current query
        messages.append({"role": "user", "content": user_prompt})

        # Call OpenAI API
        try:
            # Use more tokens for synthesis mode
            max_tokens = self.max_tokens + 200 if synthesis_mode else self.max_tokens

            # Try primary model with automatic fallback
            try:
                response = await self._call_completion(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    request_id=request_id
                )
            except Exception as e:
                if self._should_fallback(e) and self.model != self.fallback_model:
                    logger.warning("primary_model_failed_using_fallback",
                                  primary_model=self.model,
                                  fallback_model=self.fallback_model,
                                  error=str(e),
                                  request_id=request_id)
                    response = await self._call_completion(
                        model=self.fallback_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        request_id=request_id
                    )
                else:
                    raise

            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Build Citation objects with multi-source awareness
            citations = self._build_citations(chunks, answer, synthesis_mode)

            latency_ms = int((time.time() - start_time) * 1000)

            # Log diagnostics
            logger.info(
                "answer_generated",
                request_id=request_id,
                model_used=response.model,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                chunks_used=len(chunks),
                answer_length=len(answer),
                synthesis_mode=synthesis_mode,
                source_doc_count=source_doc_count
            )

            return {
                "answer": answer,
                "citations": citations,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "synthesis_mode": synthesis_mode,
                "source_doc_count": source_doc_count
            }

        except Exception as e:
            logger.error(
                "generation_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise Exception(f"Failed to generate answer: {str(e)}") from e

    def _build_citations(
        self,
        chunks: List[Dict[str, Any]],
        answer: str,
        synthesis_mode: bool
    ) -> List[Citation]:
        """
        Build Citation objects with multi-source awareness.

        Detects citation ranges in answer (e.g., [1-3]) for compact notation.
        """
        # Parse citation numbers from answer
        cited_numbers = set()
        citation_pattern = r'\[(\d+(?:-\d+)?(?:,\s*\d+)*)\]'

        for match in re.finditer(citation_pattern, answer):
            citation_ref = match.group(1)

            # Handle ranges like [1-3]
            if '-' in citation_ref:
                parts = citation_ref.split('-')
                try:
                    start = int(parts[0].strip())
                    end = int(parts[1].split(',')[0].strip())
                    cited_numbers.update(range(start, end + 1))
                except ValueError:
                    pass

            # Handle comma-separated like [1,2,3]
            for num in citation_ref.replace('-', ',').split(','):
                try:
                    cited_numbers.add(int(num.strip()))
                except ValueError:
                    pass

        citations = []
        for idx, chunk in enumerate(chunks, 1):
            snippet = chunk.get('text', '')[:200]
            if len(chunk.get('text', '')) > 200:
                snippet += "..."

            source_type = chunk.get('source', 'document')

            # Detect if part of multi-source claim (adjacent citations)
            is_multi_source = (
                synthesis_mode and
                ((idx - 1) in cited_numbers or (idx + 1) in cited_numbers) and
                idx in cited_numbers
            )

            citation = Citation(
                id=idx,
                doc_id=chunk.get('doc_id', ''),
                filename=chunk.get('filename', ''),
                page_range=chunk.get('page_range', ''),
                section_title=chunk.get('section_title'),
                snippet=snippet,
                score=chunk.get('rerank_score', chunk.get('score')),
                source=source_type,
                multi_source=is_multi_source
            )
            citations.append(citation)

        return citations
