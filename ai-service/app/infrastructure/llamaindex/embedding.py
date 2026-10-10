"""LlamaIndex embedding adapter.

This adapter keeps the rest of the codebase on the existing embedder protocol
while allowing LlamaIndex indexes to reuse the same embedding implementation.
"""

from typing import List

from pydantic import PrivateAttr
from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.ports.data_access import Embedder


class LlamaIndexEmbeddingAdapter(BaseEmbedding):
    """Wraps the project embedder in LlamaIndex's embedding interface."""

    _embedder: Embedder = PrivateAttr()

    def __init__(self, embedder: Embedder, model_name: str = "digital-me-local-embedder"):
        super().__init__(model_name=model_name)
        self._embedder = embedder

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embedder.embed(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._embedder.embed(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embedder.embed(text)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._embedder.embed(text)
