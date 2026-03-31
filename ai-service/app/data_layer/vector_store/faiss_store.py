"""FAISS vector-store backend."""

import json
from pathlib import Path
from typing import Iterable, List

from app.core.logger import logger
from app.data_layer.models import IndexedChunk, RetrievalResult
from app.data_layer.vector_store.base import BaseVectorStore


class FaissVectorStore(BaseVectorStore):
    """Persistent FAISS-backed vector store with metadata sidecar."""

    def __init__(self, index_path: str, metadata_path: str, dimensions: int = None):
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.dimensions = dimensions

    def upsert(self, chunks: Iterable[IndexedChunk]) -> None:
        items = list(chunks)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        if not items:
            self._write_empty_index()
            self._write_metadata([])
            return

        faiss = self._import_faiss()
        import numpy as np

        vectors = np.array([chunk.embedding for chunk in items], dtype="float32")
        if vectors.ndim != 2:
            raise ValueError("Expected a 2D embedding matrix for FAISS upsert")
        if self.dimensions is None:
            self.dimensions = int(vectors.shape[1])
        if vectors.shape[1] != self.dimensions:
            raise ValueError("Embedding dimensions do not match vector-store configuration")

        index = faiss.IndexFlatIP(self.dimensions)
        index.add(vectors)
        faiss.write_index(index, str(self.index_path))
        self._write_metadata(items)

        logger.info("Persisted chunks into FAISS vector store", extra={"chunks": len(items)})

    def load_chunks(self) -> List[IndexedChunk]:
        if not self.metadata_path.exists():
            return []

        payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return [IndexedChunk(**item) for item in payload]

    def search(self, query_embedding: List[float], top_k: int) -> List[RetrievalResult]:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return []

        faiss = self._import_faiss()
        import numpy as np

        metadata = self.load_chunks()
        if not metadata:
            return []

        index = faiss.read_index(str(self.index_path))
        query = np.array([query_embedding], dtype="float32")
        if query.shape[1] != index.d:
            raise ValueError("Query embedding dimensions do not match FAISS index dimensions")
        scores, indices = index.search(query, top_k)

        results: List[RetrievalResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue

            chunk = metadata[idx]
            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    text=chunk.text,
                    source_path=chunk.source_path,
                    score=float(score),
                    token_count=chunk.token_count,
                    metadata=chunk.metadata,
                )
            )

        return results

    def _write_metadata(self, chunks: List[IndexedChunk]) -> None:
        payload = [chunk.__dict__ for chunk in chunks]
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_empty_index(self) -> None:
        faiss = self._import_faiss()
        if self.dimensions is None:
            raise ValueError("Cannot create an empty FAISS index without configured dimensions")
        index = faiss.IndexFlatIP(self.dimensions)
        faiss.write_index(index, str(self.index_path))

    def _import_faiss(self):
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError(
                "faiss is required for the configured vector store. Install faiss-cpu in the project environment."
            ) from exc
        return faiss
