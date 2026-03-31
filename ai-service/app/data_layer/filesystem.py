"""Source document loader for the offline indexing pipeline."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logger import logger
from app.data_layer.models import KnowledgeDocument


class FileSystemDocumentLoader:
    """Loads local text and JSON documents from the configured data directory."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def load(self) -> List[KnowledgeDocument]:
        if not self.data_dir.exists():
            logger.warning("Data directory does not exist", extra={"path": str(self.data_dir)})
            return []

        documents: List[KnowledgeDocument] = []
        for path in sorted(self.data_dir.rglob("*")):
            if not path.is_file():
                continue
            if ".index" in path.parts:
                continue

            suffix = path.suffix.lower()
            if suffix in {".md", ".txt"}:
                document = self._load_text_document(path)
            elif suffix == ".json":
                document = self._load_json_document(path)
            else:
                continue

            if document and document.content.strip():
                documents.append(document)

        logger.info("Loaded knowledge documents", extra={"count": len(documents)})
        return documents

    def _load_text_document(self, path: Path) -> KnowledgeDocument:
        content = path.read_text(encoding="utf-8")
        title = path.stem.replace("-", " ").replace("_", " ").title()
        return KnowledgeDocument(
            document_id=self._build_document_id(path),
            title=title,
            content=content,
            source_path=str(path),
            metadata={"format": path.suffix.lower().lstrip(".")},
        )

    def _load_json_document(self, path: Path) -> Optional[KnowledgeDocument]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        title = payload.get("title") or path.stem.replace("-", " ").replace("_", " ").title()
        content = payload.get("content")

        if not content:
            content = self._render_sections(payload.get("sections", []))

        if not content:
            logger.warning("Skipping JSON document with no content", extra={"path": str(path)})
            return None

        metadata = {
            "format": "json",
            "category": str(payload.get("category", "general")),
        }
        for key, value in payload.get("metadata", {}).items():
            metadata[str(key)] = str(value)

        return KnowledgeDocument(
            document_id=self._build_document_id(path),
            title=title,
            content=content,
            source_path=str(path),
            metadata=metadata,
        )

    def _render_sections(self, sections: List[Dict[str, str]]) -> str:
        parts: List[str] = []
        for section in sections:
            heading = section.get("heading", "").strip()
            body = section.get("body", "").strip()
            if heading:
                parts.append(heading)
            if body:
                parts.append(body)
        return "\n\n".join(parts)

    def _build_document_id(self, path: Path) -> str:
        return path.relative_to(self.data_dir).as_posix()
