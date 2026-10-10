"""Repository bridge between offline vector-store indexing and online retrieval."""

import hashlib
import math
import re
from pathlib import Path
from collections import Counter
from typing import Callable, List, Optional

from app.core.config import settings
from app.core.logger import logger
from app.core.ports.cache import CacheStore
from app.core.ports import ArtifactStore, Embedder, VectorStore
from app.data_layer.embedder import build_default_embedder
from app.data_layer.models import IndexedChunk, RetrievalResult
from app.data_layer.pipeline import JsonArtifactStore, OfflineIndexingPipeline
from app.infrastructure.cache.serialization import deserialize_retrieval_results, serialize_retrieval_results
from app.rag.vector_store import build_default_vector_store


class VectorRepository:
    """Serves retrieval candidates from the configured vector store.

    The repository owns the embedding/query contract and keeps the rest of the
    application isolated from FAISS-specific details.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[Embedder] = None,
        artifact_store: Optional[ArtifactStore] = None,
        rebuild_pipeline_factory: Optional[Callable[[], OfflineIndexingPipeline]] = None,
        cache_store: Optional[CacheStore] = None,
    ):
        self.vector_store = vector_store or build_default_vector_store()
        self.embedder = embedder or build_default_embedder(settings.embedding.model)
        self.artifact_store = artifact_store or JsonArtifactStore(settings.INDEX_ARTIFACT_PATH)
        self.rebuild_pipeline_factory = rebuild_pipeline_factory
        self.cache_store = cache_store
        self.index_signature = self._build_index_signature()

    async def retrieve(self, query: str) -> List[RetrievalResult]:
        self._ensure_index()

        cache_key = self._build_cache_key(query)
        cached_results = await self._read_cache(cache_key)
        if cached_results is not None:
            logger.info("Vector retrieval cache hit", extra={"query": query, "results": len(cached_results)})
            return cached_results

        query_embedding = self.embedder.embed(query)
        results = self.vector_store.search(query_embedding=query_embedding, top_k=settings.retrieval.candidate_k)
        results = self._apply_lexical_boost(query, results)
        logger.info("Vector retrieval complete", extra={"query": query, "results": len(results)})
        await self._write_cache(cache_key, results)
        return results

    def rebuild(self) -> List[IndexedChunk]:
        if self.rebuild_pipeline_factory is None:
            raise RuntimeError("VectorRepository requires a rebuild pipeline factory for offline indexing")
        pipeline = self.rebuild_pipeline_factory()
        chunks = pipeline.run()
        self.index_signature = self._build_index_signature()
        return chunks

    async def _read_cache(self, cache_key: str) -> Optional[List[RetrievalResult]]:
        if self.cache_store is None:
            return None

        payload = await self.cache_store.get(cache_key)
        if not payload:
            return None

        try:
            return deserialize_retrieval_results(payload)
        except Exception as exc:
            logger.warning("Cached retrieval payload could not be parsed", extra={"error": str(exc)})
            return None

    async def _write_cache(self, cache_key: str, results: List[RetrievalResult]) -> None:
        if self.cache_store is None:
            return

        try:
            await self.cache_store.set(cache_key, serialize_retrieval_results(results), settings.cache.retrieval_ttl_seconds)
        except Exception as exc:
            logger.warning("Failed to cache retrieval results", extra={"error": str(exc)})

    def _ensure_index(self) -> None:
        if self.vector_store.load_chunks():
            return

        logger.info("No vector-store index found, building from source data")
        self.rebuild()

    def _build_cache_key(self, query: str) -> str:
        normalized_query = " ".join(query.strip().lower().split())
        raw = "|".join([self.index_signature, settings.embedding.model, normalized_query])
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"retrieval:{digest}"

    def _build_index_signature(self) -> str:
        parts = [
            self._path_signature(settings.INDEX_ARTIFACT_PATH),
            self._path_signature(settings.FAISS_INDEX_PATH),
            self._path_signature(settings.FAISS_METADATA_PATH),
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _path_signature(self, path_value: str) -> str:
        path = Path(path_value)
        if not path.exists():
            return "missing"

        stat = path.stat()
        return f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}"

    def _apply_lexical_boost(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        query_terms = Counter(self._tokenize(query))
        boosted: List[RetrievalResult] = []

        for result in results:
            text_boost = self._lexical_boost(query_terms, self._tokenize(result.text))
            title_boost = self._lexical_boost(query_terms, self._tokenize(result.title))
            source_boost = self._lexical_boost(query_terms, self._tokenize(result.source_path))
            lexical_boost = text_boost + (0.25 * title_boost) + (0.1 * source_boost)
            lexical_boost += self._category_boost(result.metadata)
            boosted.append(
                RetrievalResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    title=result.title,
                    text=result.text,
                    source_path=result.source_path,
                    score=result.score + lexical_boost,
                    token_count=result.token_count,
                    metadata=result.metadata,
                )
            )

        boosted.sort(key=lambda item: item.score, reverse=True)
        return boosted

    def _lexical_boost(self, query_terms: Counter, text_terms: List[str]) -> float:
        text_counter = Counter(text_terms)
        overlap = 0.0
        for token, query_freq in query_terms.items():
            overlap += min(query_freq, text_counter.get(token, 0))

        if overlap == 0:
            return 0.0

        norm = math.sqrt(sum(value * value for value in text_counter.values()))
        return overlap / max(norm, 1.0)

    def _tokenize(self, text: str) -> List[str]:
        return [token.lower() for token in re.findall(r"[a-zA-Z0-9']+", text)]

    def _category_boost(self, metadata: dict) -> float:
        category = str(metadata.get("category", "")).strip().lower()
        boosts = {
            "identity": 0.55,
            "profile": 0.45,
            "experience": 0.18,
            "project": 0.12,
            "faq": 0.08,
            "working_style": -0.12,
        }
        return boosts.get(category, 0.0)
