"""Reranking strategies for the online RAG pipeline."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Optional, Protocol, Sequence

from app.core.config import settings
from app.core.logger import logger
from app.data_layer.models import RetrievalResult


class SemanticScorer(Protocol):
    """Minimal scoring contract used by the semantic reranker."""

    def predict(self, pairs: Sequence[Sequence[str]], batch_size: int = 8, show_progress_bar: bool = False):
        ...


class HybridReranker:
    """Lightweight lexical reranker that preserves exact-match coverage."""

    def __init__(self, top_k: Optional[int] = None):
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


class SemanticCrossEncoderReranker:
    """Cross-encoder reranker with a deterministic fallback."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        top_k: Optional[int] = None,
        max_candidates: Optional[int] = None,
        batch_size: Optional[int] = None,
        scorer: Optional[SemanticScorer] = None,
        fallback: Optional[HybridReranker] = None,
    ):
        self.model_name = model_name or settings.reranking.model
        self.top_k = top_k or settings.reranking.top_k
        self.max_candidates = max_candidates or settings.reranking.max_candidates
        self.batch_size = batch_size or settings.reranking.batch_size
        self.fallback = fallback or HybridReranker(top_k=self.top_k)
        self._scorer = scorer
        self._load_failed = False

    def rank(self, query: str, candidates: Iterable[RetrievalResult]) -> List[RetrievalResult]:
        candidate_list = list(candidates)
        if not candidate_list:
            return []

        scorer = self._get_scorer()
        if scorer is None:
            return self.fallback.rank(query=query, candidates=candidate_list)

        scored_candidates = sorted(candidate_list, key=lambda item: item.score, reverse=True)[: self.max_candidates]
        pairs = [[query, candidate.text] for candidate in scored_candidates]
        scores = scorer.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)

        reranked: List[RetrievalResult] = []
        for candidate, score in zip(scored_candidates, scores):
            reranked.append(
                RetrievalResult(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    title=candidate.title,
                    text=candidate.text,
                    source_path=candidate.source_path,
                    score=float(score),
                    token_count=candidate.token_count,
                    metadata=candidate.metadata,
                )
            )

        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[: self.top_k]

    def _get_scorer(self) -> Optional[SemanticScorer]:
        if self._scorer is not None:
            return self._scorer
        if self._load_failed:
            return None

        try:
            from sentence_transformers import CrossEncoder
        except Exception as exc:
            logger.warning("Semantic reranker unavailable", extra={"reason": "sentence_transformers import failed", "error": str(exc)})
            self._load_failed = True
            return None

        try:
            self._scorer = CrossEncoder(self.model_name)
        except Exception as exc:
            logger.warning(
                "Semantic reranker unavailable",
                extra={"reason": "model loading failed", "model": self.model_name, "error": str(exc)},
            )
            self._load_failed = True
            return None

        logger.info("Semantic reranker initialized", extra={"model": self.model_name})
        return self._scorer


def build_default_reranker() -> HybridReranker:
    if not settings.reranking.enabled:
        return HybridReranker(top_k=settings.reranking.top_k)

    if settings.reranking.strategy.lower() == "semantic":
        return SemanticCrossEncoderReranker(
            model_name=settings.reranking.model,
            top_k=settings.reranking.top_k,
            max_candidates=settings.reranking.max_candidates,
            batch_size=settings.reranking.batch_size,
        )

    return HybridReranker(top_k=settings.reranking.top_k)
