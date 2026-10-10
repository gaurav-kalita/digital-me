"""Vector-store backend selection and composition."""

from typing import Optional

from app.core.config import settings
from app.rag.vector_store.base import BaseVectorStore
from app.rag.vector_store.faiss_store import FaissVectorStore


class VectorStoreFactory:
    """Factory for selecting vector-store backends from configuration."""

    @staticmethod
    def create(
        store_type: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> BaseVectorStore:
        selected_type = (store_type or settings.VECTOR_STORE_TYPE).lower()
        selected_dimensions = dimensions or settings.embedding.dimensions

        if selected_type == "faiss":
            return FaissVectorStore(
                index_path=settings.FAISS_INDEX_PATH,
                metadata_path=settings.FAISS_METADATA_PATH,
                dimensions=selected_dimensions,
            )

        raise ValueError("Unsupported vector store type: %s" % selected_type)


def build_default_vector_store() -> BaseVectorStore:
    """Backward-compatible helper for application composition."""

    return VectorStoreFactory.create()
