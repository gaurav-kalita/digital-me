"""End-to-end online RAG orchestration."""

import time
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logger import logger
from app.core.ports import ContextBuilder, LLMProvider, QueryProcessor, Reranker, RetrievalGateway
from app.data_layer.models import RetrievalResult


class RAGResult:
    """Return object used by the service layer."""

    def __init__(self, prompt: str, context_items: List[RetrievalResult], processed_query: Dict[str, Any]):
        self.prompt = prompt
        self.context_items = context_items
        self.processed_query = processed_query


class RAGAnswer:
    """Return object used when the pipeline also invokes generation."""

    def __init__(self, answer: str, prompt: str, context_items: List[RetrievalResult], processed_query: Dict[str, Any]):
        self.answer = answer
        self.prompt = prompt
        self.context_items = context_items
        self.processed_query = processed_query


class RAGPipeline:
    """Coordinates query processing, retrieval, reranking, and context building."""

    def __init__(
        self,
        query_processor: QueryProcessor,
        retriever: RetrievalGateway,
        reranker: Reranker,
        context_builder: ContextBuilder,
        provider: LLMProvider,
    ):
        self.provider = provider
        self.query_processor = query_processor
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder

    async def prepare(self, query: str) -> RAGResult:
        started_at = time.perf_counter()
        processed_query = self.query_processor.process(query)
        query_processing_ms = (time.perf_counter() - started_at) * 1000

        retrieval_started_at = time.perf_counter()
        queries = self._expand_queries(processed_query)
        candidates = await self.retriever.retrieve(queries)
        retrieval_ms = (time.perf_counter() - retrieval_started_at) * 1000

        rerank_started_at = time.perf_counter()
        ranked = self._rerank(query=query, candidates=candidates)
        rerank_ms = (time.perf_counter() - rerank_started_at) * 1000

        prompt_started_at = time.perf_counter()
        prompt, selected = self.context_builder.build(query=query, candidates=ranked)
        prompt_ms = (time.perf_counter() - prompt_started_at) * 1000

        logger.debug(
            "RAG pipeline prepared prompt",
            extra={
                "queries": len(queries),
                "candidates": len(candidates),
                "selected": len(selected),
                "query_processing_ms": round(query_processing_ms, 2),
                "retrieval_ms": round(retrieval_ms, 2),
                "rerank_ms": round(rerank_ms, 2),
                "prompt_ms": round(prompt_ms, 2),
                "total_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        return RAGResult(prompt=prompt, context_items=selected, processed_query=processed_query)

    async def answer(self, query: str) -> RAGAnswer:
        prepared = await self.prepare(query)
        answer_text = ""
        if prepared.context_items:
            try:
                generation_started_at = time.perf_counter()
                answer_text = await self.provider.generate(prepared.prompt)
                generation_ms = (time.perf_counter() - generation_started_at) * 1000
                logger.debug(
                    "Generation completed",
                    extra={
                        "provider": type(self.provider).__name__,
                        "generation_ms": round(generation_ms, 2),
                    },
                )
            except Exception as exc:
                logger.bind(
                    error=str(exc),
                    exception_type=type(exc).__name__,
                    provider=type(self.provider).__name__,
                    query=query,
                ).opt(exception=exc).warning("Generation provider failed; returning grounded fallback")
                answer_text = "I found relevant context, but the generation provider is unavailable right now."

        return RAGAnswer(
            answer=answer_text,
            prompt=prepared.prompt,
            context_items=prepared.context_items,
            processed_query=prepared.processed_query,
        )

    def _expand_queries(self, processed_query: Dict[str, Any]) -> List[str]:
        queries = []
        seen = set()

        for value in [
            processed_query.get("rewritten_query"),
            processed_query.get("normalized_query"),
            processed_query.get("original_query"),
        ]:
            if value and value not in seen:
                queries.append(value)
                seen.add(value)

        explicit_queries = processed_query.get("queries", [])
        for value in explicit_queries:
            if value and value not in seen:
                queries.append(value)
                seen.add(value)

        return queries or [processed_query.get("original_query", "")]

    def _rerank(self, query: str, candidates: List[RetrievalResult]) -> List[RetrievalResult]:
        if not settings.reranking.enabled:
            return candidates[: settings.reranking.top_k]
        return self.reranker.rank(query=query, candidates=candidates)
