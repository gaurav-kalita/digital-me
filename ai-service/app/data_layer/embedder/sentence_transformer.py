"""Sentence-transformers backed embedder."""

from typing import List

from app.data_layer.embedder.base import BaseEmbedder


class SentenceTransformerEmbedder(BaseEmbedder):
    """Embedding provider backed by sentence-transformers."""

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is required for this embedder") from exc

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()
