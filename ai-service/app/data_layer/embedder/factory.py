"""Embedder factory and selection policy."""

from typing import Optional

from app.core.config import settings
from app.core.logger import logger
from app.data_layer.embedder.base import BaseEmbedder
from app.data_layer.embedder.hashing import HashingEmbedder
from app.data_layer.embedder.sentence_transformer import SentenceTransformerEmbedder


class EmbedderFactory:
    """Factory for selecting embedder strategies from configuration."""

    @staticmethod
    def create(
        embedder_type: Optional[str] = None,
        model_name: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> BaseEmbedder:
        selected_type = (embedder_type or settings.embedding.strategy).lower()
        selected_model = model_name or settings.embedding.model
        selected_dimensions = dimensions or settings.embedding.dimensions

        if selected_type in {"hash", "hashing", "fallback"}:
            return HashingEmbedder(dimensions=selected_dimensions)

        if selected_type in {"sentence_transformer", "sentence-transformer", "st"}:
            return SentenceTransformerEmbedder(
                selected_model,
                local_files_only=settings.embedding.local_files_only,
            )

        if selected_type == "auto":
            if selected_model:
                try:
                    logger.info("Using sentence-transformer embedder", extra={"model": selected_model})
                    return SentenceTransformerEmbedder(
                        selected_model,
                        local_files_only=settings.embedding.local_files_only,
                    )
                except Exception:
                    logger.opt(exception=True).warning(
                        "Falling back to hashing embedder because sentence-transformer init failed"
                    )
            return HashingEmbedder(dimensions=selected_dimensions)

        raise ValueError("Unsupported embedder type: %s" % selected_type)


def build_default_embedder(model_name: Optional[str] = None):
    """Backward-compatible helper for existing call sites."""

    return EmbedderFactory.create(model_name=model_name)
