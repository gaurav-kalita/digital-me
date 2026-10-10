"""Sentence-transformers backed embedder."""

from typing import List

from app.data_layer.embedder.base import BaseEmbedder


class SentenceTransformerEmbedder(BaseEmbedder):
    """Embedding provider backed by sentence-transformers."""

    def __init__(self, model_name: str, local_files_only: bool = True):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is required for this embedder") from exc

        self.model_name = model_name
        self.local_files_only = local_files_only
        self.model = SentenceTransformer(model_name, local_files_only=local_files_only)

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()
