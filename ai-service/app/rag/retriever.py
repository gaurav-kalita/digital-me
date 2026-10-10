"""Retrieval layer for the online RAG pipeline."""

import math
import re
from collections import Counter
from typing import Iterable, List

from app.core.logger import logger
from app.core.ports import RetrievalGateway
from app.data_layer.models import RetrievalResult
from app.repositories.vector_repository import VectorRepository

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9']+")


class Retriever(RetrievalGateway):
    """Runs vector retrieval across query variants and fuses scores.

    FAISS provides dense retrieval. This layer adds a sparse lexical fusion
    boost so we retain exact-match benefits without coupling the vector store to
    a specific hybrid-search database API.
    """

    def __init__(self, repository: VectorRepository):
        self.repository = repository

    async def retrieve(self, queries: Iterable[str]) -> List[RetrievalResult]:
        deduped = {}
        for query in queries:
            results = await self.repository.retrieve(query)
            for result in results:
                lexical_boost = self._sparse_score(query, result.text)
                fused_score = result.score + lexical_boost
                existing = deduped.get(result.chunk_id)
                candidate = RetrievalResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    title=result.title,
                    text=result.text,
                    source_path=result.source_path,
                    score=fused_score,
                    token_count=result.token_count,
                    metadata=result.metadata,
                )
                if existing is None or candidate.score > existing.score:
                    deduped[result.chunk_id] = candidate

        merged_results = list(deduped.values())
        merged_results.sort(key=lambda item: item.score, reverse=True)
        logger.info("Merged retrieval results", extra={"results": len(merged_results)})
        return merged_results

    def _sparse_score(self, query: str, text: str) -> float:
        query_terms = Counter(self._tokenize(query))
        text_terms = Counter(self._tokenize(text))

        overlap = 0.0
        for token, query_freq in query_terms.items():
            overlap += min(query_freq, text_terms.get(token, 0))

        if overlap == 0:
            return 0.0

        norm = math.sqrt(sum(value * value for value in text_terms.values()))
        return overlap / max(norm, 1.0)

    def _tokenize(self, text: str) -> List[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]
