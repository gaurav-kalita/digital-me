"""End-to-end online RAG orchestration."""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.data_layer.models import RetrievalResult
from app.rag.contextBuilder import ContextBuilder
from app.rag.reranker import HybridReranker
from app.rag.retriever import Retriever


class DefaultQueryProcessor:
    """Adapter around the existing query-processing module.

    The dedicated `query_processing` package already exists in the repo. This
    wrapper keeps the online pipeline decoupled from any specific
    implementation and provides sensible fallbacks when advanced components are
    unavailable.
    """

    def process(self, query: str) -> Dict[str, Any]:
        normalized = " ".join(query.strip().split())
        return {
            "original_query": query,
            "normalized_query": normalized,
            "rewritten_query": normalized,
            "embedding": [],
            "metadata": {},
            "queries": [normalized],
        }


class RAGResult:
    """Return object used by the service layer."""

    def __init__(self, prompt: str, context_items: List[RetrievalResult], processed_query: Dict[str, Any]):
        self.prompt = prompt
        self.context_items = context_items
        self.processed_query = processed_query


class RAGPipeline:
    """Coordinates query processing, retrieval, reranking, and context building."""

    def __init__(
        self,
        query_processor=None,
        retriever: Optional[Retriever] = None,
        reranker: Optional[HybridReranker] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.query_processor = query_processor or DefaultQueryProcessor()
        self.retriever = retriever or Retriever()
        self.reranker = reranker or HybridReranker()
        self.context_builder = context_builder or ContextBuilder()

    async def prepare(self, query: str) -> RAGResult:
        processed_query = self.query_processor.process(query)
        queries = self._expand_queries(processed_query)
        candidates = await self.retriever.retrieve(queries)
        ranked = self._rerank(query=query, candidates=candidates)
        prompt, selected = self.context_builder.build(query=query, candidates=ranked)

        logger.info(
            "RAG pipeline prepared prompt",
            extra={
                "queries": len(queries),
                "candidates": len(candidates),
                "selected": len(selected),
            },
        )
        return RAGResult(prompt=prompt, context_items=selected, processed_query=processed_query)

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
