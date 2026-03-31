import asyncio
import json
import shutil
import uuid
from pathlib import Path

from app.data_layer.chunker import (
    ChunkerFactory,
    HuggingFaceChunker,
    TiktokenChunker,
    TokenChunker,
    WordTokenChunker,
)
from app.data_layer.cleaner import AggressiveCleaner, CleanerFactory, TextNormalizer
from app.data_layer.embedder import EmbedderFactory, HashingEmbedder
from app.data_layer.filesystem import FileSystemDocumentLoader
from app.data_layer.index import HybridSearchIndex
from app.data_layer.models import IndexedChunk, KnowledgeDocument
from app.data_layer.pipeline import JsonArtifactStore, OfflineIndexingPipeline
from app.data_layer.vector_store import FaissVectorStore, VectorStoreFactory
from app.repositories.vector_repository import VectorRepository


class FakeEncoding:
    def encode(self, text: str):
        return [index + 1 for index, _ in enumerate(text.split())]

    def decode(self, token_ids):
        return " ".join("tok%s" % token_id for token_id in token_ids)


class FakeHFTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False):
        return [index + 100 for index, _ in enumerate(text.split())]

    def decode(self, token_ids, skip_special_tokens: bool = True):
        return " ".join("hf%s" % token_id for token_id in token_ids)


def _workspace_temp_dir() -> Path:
    root = Path.cwd() / "test_scratch"
    root.mkdir(exist_ok=True)
    temp_dir = root / ("rag-tests-" + uuid.uuid4().hex)
    temp_dir.mkdir()
    return temp_dir


def test_filesystem_loader_reads_json_sections():
    temp_dir = _workspace_temp_dir()
    try:
        doc_path = temp_dir / "profile.json"
        doc_path.write_text(
            json.dumps(
                {
                    "title": "Profile",
                    "sections": [
                        {"heading": "About", "body": "Gaurav builds AI products."},
                        {"heading": "Focus", "body": "Retrieval and orchestration."},
                    ],
                }
            ),
            encoding="utf-8",
        )

        loader = FileSystemDocumentLoader(str(temp_dir))
        documents = loader.load()

        assert len(documents) == 1
        assert documents[0].title == "Profile"
        assert "Gaurav builds AI products." in documents[0].content
        assert documents[0].document_id == "profile.json"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cleaner_factory_supports_strategy_selection():
    conservative = CleanerFactory.create("conservative")
    aggressive = CleanerFactory.create("aggressive")

    assert isinstance(conservative, TextNormalizer)
    assert isinstance(aggressive, AggressiveCleaner)
    assert aggressive.clean("<p>Hello</p>   world") == "Hello world"


def test_token_chunker_creates_overlapping_chunks():
    chunker = TokenChunker(chunk_size_tokens=4, chunk_overlap_tokens=1)
    document = KnowledgeDocument(
        document_id="doc-1",
        title="Doc",
        content="one two three four five six seven",
        source_path="doc.txt",
        metadata={},
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 2
    assert chunks[0].text == "one two three four"
    assert chunks[1].text == "four five six seven"


def test_tiktoken_chunker_creates_real_token_bounded_chunks():
    chunker = TiktokenChunker(
        chunk_size_tokens=8,
        chunk_overlap_tokens=2,
        encoding_name="cl100k_base",
        encoding=FakeEncoding(),
    )
    document = KnowledgeDocument(
        document_id="doc-2",
        title="Doc",
        content="Retrieval augmented generation systems depend on strong chunking strategies and token-aware context windows.",
        source_path="doc.txt",
        metadata={},
    )

    chunks = chunker.chunk(document)

    assert chunks
    assert all(chunk.token_count <= 8 for chunk in chunks)
    assert len(chunks) >= 2


def test_chunker_factory_supports_plug_and_play_selection():
    word_chunker = ChunkerFactory.create(chunker_type="word", chunk_size_tokens=10, chunk_overlap_tokens=2)
    tokenizer_chunker = ChunkerFactory.create(
        chunker_type="tiktoken",
        chunk_size_tokens=10,
        chunk_overlap_tokens=2,
        encoding_name="cl100k_base",
        encoding=FakeEncoding(),
    )
    huggingface_chunker = ChunkerFactory.create(
        chunker_type="huggingface",
        chunk_size_tokens=10,
        chunk_overlap_tokens=2,
        tokenizer=FakeHFTokenizer(),
    )

    assert isinstance(word_chunker, WordTokenChunker)
    assert isinstance(tokenizer_chunker, TiktokenChunker)
    assert isinstance(huggingface_chunker, HuggingFaceChunker)


def test_chunker_factory_falls_back_when_tokenizer_is_unavailable():
    tokenizer_chunker = ChunkerFactory.create(
        chunker_type="tiktoken",
        chunk_size_tokens=10,
        chunk_overlap_tokens=2,
        encoding_name="definitely-not-a-real-encoding",
    )

    assert isinstance(tokenizer_chunker, WordTokenChunker)


def test_huggingface_chunker_uses_injected_tokenizer():
    chunker = HuggingFaceChunker(
        chunk_size_tokens=6,
        chunk_overlap_tokens=2,
        model_name="bert-base-uncased",
        tokenizer=FakeHFTokenizer(),
    )
    document = KnowledgeDocument(
        document_id="doc-3",
        title="Doc",
        content="Hugging face token based chunking should stay pluggable and deterministic in tests.",
        source_path="doc.txt",
        metadata={},
    )

    chunks = chunker.chunk(document)

    assert chunks
    assert all(chunk.token_count <= 6 for chunk in chunks)


def test_offline_pipeline_persists_embedded_chunks():
    temp_dir = _workspace_temp_dir()
    try:
        data_dir = temp_dir / "data"
        artifact_path = temp_dir / ".index" / "chunks.json"
        faiss_index_path = temp_dir / ".index" / "chunks.faiss"
        faiss_metadata_path = temp_dir / ".index" / "chunks.metadata.json"
        data_dir.mkdir()
        (data_dir / "profile.txt").write_text("Gaurav builds retrieval systems locally.", encoding="utf-8")

        pipeline = OfflineIndexingPipeline(
            loader=FileSystemDocumentLoader(str(data_dir)),
            cleaner=TextNormalizer(),
            chunker=TokenChunker(chunk_size_tokens=50, chunk_overlap_tokens=10),
            embedder=HashingEmbedder(dimensions=32),
            vector_store=FaissVectorStore(
                index_path=str(faiss_index_path),
                metadata_path=str(faiss_metadata_path),
                dimensions=32,
            ),
            artifact_store=JsonArtifactStore(str(artifact_path)),
        )

        chunks = pipeline.run()
        stored_chunks = JsonArtifactStore(str(artifact_path)).load()
        vector_results = FaissVectorStore(
            index_path=str(faiss_index_path),
            metadata_path=str(faiss_metadata_path),
            dimensions=32,
        ).search(HashingEmbedder(dimensions=32).embed("retrieval systems"), top_k=3)

        assert chunks
        assert stored_chunks
        assert len(stored_chunks[0].embedding) == 32
        assert vector_results
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_embedder_factory_supports_hashing_strategy():
    embedder = EmbedderFactory.create(embedder_type="hashing", dimensions=32)
    vector = embedder.embed("retrieval systems")

    assert isinstance(embedder, HashingEmbedder)
    assert len(vector) == 32


def test_vector_store_factory_supports_faiss_strategy():
    vector_store = VectorStoreFactory.create(store_type="faiss", dimensions=32)

    assert isinstance(vector_store, FaissVectorStore)


def test_hybrid_search_index_ranks_relevant_chunks():
    index = HybridSearchIndex(embedder=HashingEmbedder(dimensions=32))
    index.build(
        [
            IndexedChunk(
                chunk_id="profile::0",
                document_id="profile",
                title="Profile",
                text="Gaurav is building Digital Me with retrieval augmented generation.",
                source_path="profile.json",
                token_count=10,
                embedding=HashingEmbedder(dimensions=32).embed(
                    "Gaurav is building Digital Me with retrieval augmented generation."
                ),
                metadata={"category": "profile"},
            ),
            IndexedChunk(
                chunk_id="hobby::0",
                document_id="hobby",
                title="Hobby",
                text="Weekend football and travel notes.",
                source_path="hobby.txt",
                token_count=5,
                embedding=HashingEmbedder(dimensions=32).embed("Weekend football and travel notes."),
                metadata={"category": "hobby"},
            ),
        ]
    )

    results = index.search("retrieval generation", top_k=2)

    assert len(results) == 1
    assert results[0].title == "Profile"


def test_vector_repository_reads_from_offline_artifact():
    repository = VectorRepository()
    repository.rebuild()

    results = asyncio.run(repository.retrieve("architecture retrieval"))

    assert results
    assert results[0].title == "Gaurav Profile"
