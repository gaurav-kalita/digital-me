"""Experimental LlamaIndex retrieval adapter."""

from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from app.core.logger import logger
from app.core.ports import RetrievalGateway
from app.core.ports.data_access import DocumentLoader, Embedder
from app.data_layer.models import KnowledgeDocument, RetrievalResult
from app.infrastructure.llamaindex.embedding import LlamaIndexEmbeddingAdapter


class LlamaIndexRetrievalGateway(RetrievalGateway):
    """Builds an experimental retrieval index with LlamaIndex.

    The gateway keeps the rest of the RAG pipeline unchanged. It swaps only the
    retrieval implementation, which makes it useful for experimentation and for
    richer citation metadata while leaving reranking and prompt construction in
    the existing application layer.
    """

    def __init__(
        self,
        document_loader: DocumentLoader,
        embedder: Embedder,
        top_k: int,
        chunk_size: int,
        chunk_overlap: int,
        index_factory: Optional[Callable[[Sequence[Document], LlamaIndexEmbeddingAdapter], VectorStoreIndex]] = None,
    ):
        self.document_loader = document_loader
        self.embedder = embedder
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.index_factory = index_factory or self._build_index
        self._index: Optional[VectorStoreIndex] = None
        self._signature = ""

    async def retrieve(self, queries: Iterable[str]) -> List[RetrievalResult]:
        self._ensure_index()
        if self._index is None:
            return []

        deduped: Dict[str, RetrievalResult] = {}
        retriever = self._index.as_retriever(similarity_top_k=self.top_k)

        for query in queries:
            for node_with_score in retriever.retrieve(query):
                result = self._to_retrieval_result(node_with_score)
                existing = deduped.get(result.chunk_id)
                if existing is None or result.score > existing.score:
                    deduped[result.chunk_id] = result

        merged_results = list(deduped.values())
        merged_results.sort(key=lambda item: item.score, reverse=True)
        logger.info("LlamaIndex retrieval complete", extra={"results": len(merged_results)})
        return merged_results

    def _ensure_index(self) -> None:
        documents = self.document_loader.load()
        signature = self._build_signature(documents)
        if self._index is not None and signature == self._signature:
            return

        if not documents:
            self._index = None
            self._signature = signature
            return

        self._index = self.index_factory(
            self._to_llama_documents(documents),
            LlamaIndexEmbeddingAdapter(self.embedder),
        )
        self._signature = signature

    def _build_index(
        self,
        documents: Sequence[Document],
        embed_model: LlamaIndexEmbeddingAdapter,
    ) -> VectorStoreIndex:
        effective_chunk_size = self._resolve_chunk_size(documents)
        transformations = [
            SentenceSplitter(
                chunk_size=effective_chunk_size,
                chunk_overlap=min(self.chunk_overlap, max(effective_chunk_size - 1, 1)),
            ),
        ]
        return VectorStoreIndex.from_documents(
            documents,
            transformations=transformations,
            embed_model=embed_model,
        )

    def _resolve_chunk_size(self, documents: Sequence[Document]) -> int:
        longest_metadata = 0
        splitter = SentenceSplitter(chunk_size=max(self.chunk_size, self.chunk_overlap + 1), chunk_overlap=0)

        for document in documents:
            metadata = document.metadata or {}
            metadata_str = "\n".join("%s: %s" % (key, value) for key, value in metadata.items())
            if not metadata_str:
                continue
            metadata_length = len(splitter._tokenizer(metadata_str))
            if metadata_length > longest_metadata:
                longest_metadata = metadata_length

        return max(self.chunk_size, longest_metadata + 8, self.chunk_overlap + 1)

    def _to_llama_documents(self, documents: Sequence[KnowledgeDocument]) -> List[Document]:
        llama_documents: List[Document] = []
        for document in documents:
            metadata = {
                "document_id": document.document_id,
                "source_path": document.source_path,
                "title": document.title,
                "citation_label": self._build_citation_label(document),
                "source_type": document.metadata.get("source_type", "knowledge_document"),
            }
            if "category" in document.metadata:
                metadata["category"] = document.metadata["category"]
            llama_documents.append(
                Document(
                    text=document.content,
                    metadata=metadata,
                    id_=document.document_id,
                )
            )
        return llama_documents

    def _to_retrieval_result(self, node_with_score) -> RetrievalResult:
        node = node_with_score.node
        metadata = {str(key): str(value) for key, value in (node.metadata or {}).items()}
        source_path = metadata.get("source_path") or metadata.get("file_path") or metadata.get("document_id") or ""
        title = metadata.get("title") or self._build_title(source_path)
        text = node.get_content()
        token_count = int(metadata.get("token_count") or max(len(text.split()), 1))

        metadata.setdefault("source_path", source_path)
        metadata.setdefault("title", title)
        metadata.setdefault("citation_label", metadata.get("citation_label") or self._build_citation_label_from_values(title, source_path))
        metadata["retrieval_backend"] = "llamaindex"

        return RetrievalResult(
            chunk_id=metadata.get("chunk_id") or node.node_id,
            document_id=metadata.get("document_id") or source_path or node.node_id,
            title=title,
            text=text,
            source_path=source_path or node.node_id,
            score=float(node_with_score.score or 0.0),
            token_count=token_count,
            metadata=metadata,
        )

    def _build_signature(self, documents: Sequence[KnowledgeDocument]) -> str:
        values: List[str] = []
        for document in documents:
            path = Path(document.source_path)
            if path.exists():
                stat = path.stat()
                values.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
            else:
                values.append(document.document_id)
        return "|".join(values)

    def _build_citation_label(self, document: KnowledgeDocument) -> str:
        return self._build_citation_label_from_values(document.title, document.source_path)

    def _build_citation_label_from_values(self, title: str, source_path: str) -> str:
        filename = Path(source_path).name if source_path else ""
        if title and filename and title.lower() != Path(filename).stem.replace("-", " ").replace("_", " ").lower():
            return f"{title} ({filename})"
        if title:
            return title
        return filename or source_path or "Unknown source"

    def _build_title(self, source_path: str) -> str:
        return Path(source_path).stem.replace("-", " ").replace("_", " ").title()
