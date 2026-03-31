"""Repository bridge between offline vector-store indexing and online retrieval."""

from typing import List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.data_layer.embedder import build_default_embedder
from app.data_layer.interfaces import Embedder, VectorStore
from app.data_layer.models import IndexedChunk, RetrievalResult
from app.data_layer.pipeline import JsonArtifactStore, build_default_offline_pipeline
from app.data_layer.vector_store import build_default_vector_store


class VectorRepository:
    """Serves retrieval candidates from the configured vector store.

    The repository owns the embedding/query contract and keeps the rest of the
    application isolated from FAISS-specific details.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[Embedder] = None,
        artifact_store: Optional[JsonArtifactStore] = None,
    ):
        self.vector_store = vector_store or build_default_vector_store()
        self.embedder = embedder or build_default_embedder(settings.embedding.model)
        self.artifact_store = artifact_store or JsonArtifactStore(settings.INDEX_ARTIFACT_PATH)

    async def retrieve(self, query: str) -> List[RetrievalResult]:
        self._ensure_index()
        query_embedding = self.embedder.embed(query)
        results = self.vector_store.search(query_embedding=query_embedding, top_k=settings.retrieval.candidate_k)
        logger.info("Vector retrieval complete", extra={"query": query, "results": len(results)})
        return results

    def rebuild(self) -> List[IndexedChunk]:
        pipeline = build_default_offline_pipeline(
            data_dir=settings.DATA_DIR,
            artifact_path=settings.INDEX_ARTIFACT_PATH,
            embedding_model=settings.embedding.model,
        )
        return pipeline.run()

    def _ensure_index(self) -> None:
        if self.vector_store.load_chunks():
            return

        logger.info("No vector-store index found, building from source data")
        self.rebuild()
