import asyncio
import shutil
import uuid
from pathlib import Path

from app.data_layer.embedder import HashingEmbedder
from app.data_layer.models import KnowledgeDocument
from app.infrastructure.llamaindex.loader import CompositeDocumentLoader, LlamaIndexDocumentLoader
from app.infrastructure.llamaindex.retrieval import LlamaIndexRetrievalGateway


def _workspace_temp_dir() -> Path:
    root = Path.cwd() / "test_scratch"
    root.mkdir(exist_ok=True)
    temp_dir = root / ("llamaindex-tests-" + uuid.uuid4().hex)
    temp_dir.mkdir()
    return temp_dir


def test_llamaindex_document_loader_converts_documents_and_preserves_source_metadata():
    temp_dir = _workspace_temp_dir()
    try:
        doc_path = temp_dir / "profile.txt"
        doc_path.write_text(
            "Digital Me uses a retrieval architecture with grounded citations.",
            encoding="utf-8",
        )

        loader = LlamaIndexDocumentLoader(str(temp_dir), required_exts=[".txt"])
        documents = loader.load()

        assert len(documents) == 1
        assert documents[0].document_id == "profile.txt"
        assert documents[0].title == "Profile"
        assert documents[0].source_path.endswith("profile.txt")
        assert "retrieval architecture" in documents[0].content
        assert documents[0].metadata["source_type"] == "llamaindex"
        assert documents[0].metadata["citation_label"] == "Profile"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_composite_document_loader_deduplicates_documents():
    class FakeLoader:
        def __init__(self, documents):
            self.documents = documents

        def load(self):
            return self.documents

    docs_a = [
        KnowledgeDocument(
            document_id="shared",
            title="Shared",
            content="one",
            source_path="shared.txt",
            metadata={},
        )
    ]
    docs_b = [
        KnowledgeDocument(
            document_id="shared",
            title="Shared",
            content="one",
            source_path="shared.txt",
            metadata={},
        ),
        KnowledgeDocument(
            document_id="unique",
            title="Unique",
            content="two",
            source_path="unique.txt",
            metadata={},
        ),
    ]

    loader = CompositeDocumentLoader([FakeLoader(docs_a), FakeLoader(docs_b)])
    documents = loader.load()

    assert len(documents) == 2
    assert {document.document_id for document in documents} == {"shared", "unique"}


def test_llamaindex_retrieval_gateway_returns_cited_results():
    temp_dir = _workspace_temp_dir()
    try:
        (temp_dir / "profile.txt").write_text(
            "Digital Me uses a retrieval architecture for a grounded personal assistant.",
            encoding="utf-8",
        )
        (temp_dir / "hobby.txt").write_text(
            "Weekend football and travel notes.",
            encoding="utf-8",
        )

        gateway = LlamaIndexRetrievalGateway(
            document_loader=LlamaIndexDocumentLoader(str(temp_dir), required_exts=[".txt"]),
            embedder=HashingEmbedder(dimensions=64),
            top_k=1,
            chunk_size=32,
            chunk_overlap=4,
        )

        results = asyncio.run(gateway.retrieve(["retrieval architecture"]))

        assert results
        assert results[0].source_path.endswith("profile.txt")
        assert results[0].metadata["retrieval_backend"] == "llamaindex"
        assert "citation_label" in results[0].metadata
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
