"""Hybrid search index used by the online retrieval pipeline.

This combines:
- dense similarity using chunk embeddings
- sparse lexical overlap for exact-match recall

The implementation is local and lightweight, but the abstraction mirrors how a
production RAG stack would sit in front of Qdrant/Pinecone/Weaviate plus a
keyword index.
"""

import math
import re
from collections import Counter
from typing import Iterable, List

from app.data_layer.embedder import build_default_embedder
from app.data_layer.models import IndexedChunk, RetrievalResult


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9']+")


class HybridSearchIndex:
    """In-memory hybrid search over indexed chunks."""

    def __init__(self, embedder=None, dense_weight: float = 0.65, sparse_weight: float = 0.35):
        self.embedder = embedder or build_default_embedder()
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self._chunks: List[IndexedChunk] = []
        self._chunk_tokens: List[Counter] = []

    def build(self, chunks: Iterable[IndexedChunk]) -> None:
        self._chunks = list(chunks)
        self._chunk_tokens = [Counter(self._tokenize(chunk.text)) for chunk in self._chunks]

    def search(self, query: str, top_k: int) -> List[RetrievalResult]:
        if not query.strip():
            return []

        query_embedding = self.embedder.embed(query)
        query_terms = Counter(self._tokenize(query))

        results: List[RetrievalResult] = []
        for chunk, chunk_terms in zip(self._chunks, self._chunk_tokens):
            dense_score = self._cosine_similarity(query_embedding, chunk.embedding)
            sparse_score = self._sparse_score(query_terms, chunk_terms)
            score = (dense_score * self.dense_weight) + (sparse_score * self.sparse_weight)
            if score <= 0:
                continue

            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    text=chunk.text,
                    source_path=chunk.source_path,
                    score=score,
                    token_count=chunk.token_count,
                    metadata=chunk.metadata,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def _sparse_score(self, query_terms: Counter, chunk_terms: Counter) -> float:
        overlap = 0.0
        for token, query_freq in query_terms.items():
            if token in chunk_terms:
                overlap += min(query_freq, chunk_terms[token])

        if overlap == 0:
            return 0.0

        norm = math.sqrt(sum(value * value for value in chunk_terms.values()))
        return overlap / max(norm, 1.0)

    def _cosine_similarity(self, left: List[float], right: List[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    def _tokenize(self, text: str) -> List[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]
