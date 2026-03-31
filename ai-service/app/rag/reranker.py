"""Reranking strategies for the online RAG pipeline."""

from collections import Counter
from typing import Iterable, List

from app.core.config import settings
from app.data_layer.models import RetrievalResult


class HybridReranker:
    """Lightweight reranker that boosts exact term coverage over retriever output.

    In a larger deployment this interface can be backed by a cross-encoder or
    LLM reranker. For now it improves precision without introducing network or
    GPU requirements.
    """

    def __init__(self, top_k: int = None):
        self.top_k = top_k or settings.reranking.top_k

    def rank(self, query: str, candidates: Iterable[RetrievalResult]) -> List[RetrievalResult]:
        query_terms = Counter(query.lower().split())
        reranked: List[RetrievalResult] = []

        for candidate in candidates:
            lexical_boost = self._lexical_boost(query_terms, candidate.text.lower().split())
            score = candidate.score + lexical_boost
            reranked.append(
                RetrievalResult(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    title=candidate.title,
                    text=candidate.text,
                    source_path=candidate.source_path,
                    score=score,
                    token_count=candidate.token_count,
                    metadata=candidate.metadata,
                )
            )

        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[: self.top_k]

    def _lexical_boost(self, query_terms: Counter, text_terms: List[str]) -> float:
        if not text_terms:
            return 0.0

        text_counter = Counter(text_terms)
        overlap = 0.0
        for token, query_freq in query_terms.items():
            overlap += min(query_freq, text_counter.get(token, 0))

        return overlap / max(len(text_terms), 1)
