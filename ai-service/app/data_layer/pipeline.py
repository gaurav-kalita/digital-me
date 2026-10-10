"""Offline indexing pipeline.

This module turns raw local files into vector-store entries. It also writes a
JSON artifact for observability and portability, but the primary persistence
target is the configured vector store.
"""

import json
from pathlib import Path
from typing import Iterable, List, Optional

from app.core.logger import logger
from app.core.ports import ArtifactStore, Chunker, DocumentLoader, Embedder, TextCleaner, VectorStore
from app.data_layer.models import IndexedChunk, KnowledgeDocument


class JsonArtifactStore:
    """Persists indexed chunks as a human readable artifact for debugging and rebuilds."""

    def __init__(self, artifact_path: str):
        self.artifact_path = Path(artifact_path)

    def save(self, chunks: Iterable[IndexedChunk]) -> None:
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [chunk.__dict__ for chunk in chunks]
        self.artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> List[IndexedChunk]:
        if not self.artifact_path.exists():
            return []

        payload = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        return [IndexedChunk(**item) for item in payload]


class OfflineIndexingPipeline:
    """Runs: load -> clean -> chunk -> embed -> store in vector DB + artifact."""

    def __init__(
        self,
        loader: DocumentLoader,
        cleaner: TextCleaner,
        chunker: Chunker,
        embedder: Embedder,
        vector_store: VectorStore,
        artifact_store: Optional[ArtifactStore] = None,
    ):
        self.loader = loader
        self.cleaner = cleaner
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.artifact_store = artifact_store

    def run(self) -> List[IndexedChunk]:
        documents = self.loader.load()
        normalized_documents = [self._normalize_document(document) for document in documents]

        indexed_chunks: List[IndexedChunk] = []
        for document in normalized_documents:
            for chunk in self.chunker.chunk(document):
                indexed_chunks.append(
                    IndexedChunk(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        title=chunk.title,
                        text=chunk.text,
                        source_path=chunk.source_path,
                        token_count=chunk.token_count,
                        embedding=self.embedder.embed(chunk.text),
                        metadata=chunk.metadata,
                    )
                )

        # This writes vectors into your vector store.
        self.vector_store.upsert(indexed_chunks)
        if self.artifact_store is not None:
            self.artifact_store.save(indexed_chunks)

        logger.info("Offline indexing complete", extra={"chunks": len(indexed_chunks)})
        return indexed_chunks

    def _normalize_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        return KnowledgeDocument(
            document_id=document.document_id,
            title=document.title,
            content=self.cleaner.clean(document.content),
            source_path=document.source_path,
            metadata=document.metadata,
        )
