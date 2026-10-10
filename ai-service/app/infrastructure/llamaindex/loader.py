"""LlamaIndex document loader adapters."""

from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from llama_index.core import SimpleDirectoryReader

from app.core.logger import logger
from app.core.ports.data_access import DocumentLoader
from app.data_layer.models import KnowledgeDocument

DEFAULT_EXTRA_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".html",
    ".htm",
    ".csv",
    ".xml",
    ".ppt",
    ".pptx",
    ".epub",
    ".rtf",
)


class CompositeDocumentLoader(DocumentLoader):
    """Combines multiple loaders and deduplicates documents by source path."""

    def __init__(self, loaders: Sequence[DocumentLoader]):
        if not loaders:
            raise ValueError("CompositeDocumentLoader requires at least one loader")
        self.loaders = list(loaders)

    def load(self) -> List[KnowledgeDocument]:
        deduped: Dict[str, KnowledgeDocument] = {}
        for loader in self.loaders:
            for document in loader.load():
                key = document.source_path or document.document_id
                if key not in deduped:
                    deduped[key] = document

        return list(deduped.values())


class LlamaIndexDocumentLoader(DocumentLoader):
    """Loads non-native document formats through LlamaIndex readers.

    The loader intentionally focuses on the formats that the native filesystem
    loader does not handle. That keeps the current local text/JSON pipeline in
    place while extending ingest coverage for PDFs, Office documents, and HTML.
    """

    def __init__(
        self,
        data_dir: str,
        required_exts: Optional[Sequence[str]] = None,
        reader_factory: Optional[Callable[..., SimpleDirectoryReader]] = None,
    ):
        self.data_dir = Path(data_dir)
        self.required_exts = tuple(required_exts or DEFAULT_EXTRA_EXTENSIONS)
        self.reader_factory = reader_factory or self._build_reader

    def load(self) -> List[KnowledgeDocument]:
        if not self.data_dir.exists():
            logger.warning("LlamaIndex data directory does not exist", extra={"path": str(self.data_dir)})
            return []

        try:
            reader = self.reader_factory()
            documents = reader.load_data()
        except Exception as exc:
            logger.warning(
                "LlamaIndex document loading failed; continuing without extra document types",
                extra={"path": str(self.data_dir), "error": str(exc), "exception_type": type(exc).__name__},
            )
            return []

        knowledge_documents: List[KnowledgeDocument] = []
        for document in documents:
            metadata = self._normalize_metadata(getattr(document, "metadata", {}) or {})
            source_path = metadata.get("source_path") or metadata.get("file_path") or metadata.get("absolute_path")
            if not source_path:
                continue
            if ".index" in Path(source_path).parts:
                continue

            content = getattr(document, "text", None) or getattr(document, "get_content", lambda: "")()
            if not content.strip():
                continue

            title = metadata.get("title") or self._build_title(metadata, source_path)
            document_id = metadata.get("document_id") or metadata.get("relative_path") or source_path
            metadata.setdefault("citation_label", title)

            knowledge_documents.append(
                KnowledgeDocument(
                    document_id=document_id,
                    title=title,
                    content=content,
                    source_path=source_path,
                    metadata=metadata,
                )
            )

        logger.info("Loaded LlamaIndex knowledge documents", extra={"count": len(knowledge_documents)})
        return knowledge_documents

    def _build_reader(self) -> SimpleDirectoryReader:
        return SimpleDirectoryReader(
            input_dir=str(self.data_dir),
            recursive=True,
            exclude_hidden=True,
            errors="ignore",
            filename_as_id=True,
            required_exts=list(self.required_exts),
            file_metadata=self._build_file_metadata,
        )

    def _build_file_metadata(self, file_path: str) -> Dict[str, str]:
        path = Path(file_path)
        try:
            relative_path = path.resolve().relative_to(self.data_dir.resolve()).as_posix()
        except Exception:
            relative_path = path.name

        return {
            "source_path": str(path),
            "relative_path": relative_path,
            "document_id": relative_path,
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
            "title": path.stem.replace("-", " ").replace("_", " ").title(),
            "citation_label": path.stem.replace("-", " ").replace("_", " ").title(),
            "source_type": "llamaindex",
        }

    def _normalize_metadata(self, metadata: Dict[str, object]) -> Dict[str, str]:
        normalized: Dict[str, str] = {}
        for key, value in metadata.items():
            normalized[str(key)] = str(value)
        return normalized

    def _build_title(self, metadata: Dict[str, str], source_path: str) -> str:
        file_name = metadata.get("file_name") or Path(source_path).name
        return Path(file_name).stem.replace("-", " ").replace("_", " ").title()
