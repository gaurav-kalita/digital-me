from app.providers.base import BaseLLMProvider
from app.data_layer.models import RetrievalResult
from app.rag.pipeline import RAGPipeline
from app.rag.query_processing.factory import build_query_processing_pipeline
from app.rag.context_builder import ContextBuilder
from app.rag.reranker import HybridReranker, SemanticCrossEncoderReranker
from app.repositories.vector_repository import VectorRepository


def test_reranker_prioritizes_query_overlap():
    reranker = HybridReranker(top_k=2)
    results = reranker.rank(
        "retrieval architecture",
        [
            RetrievalResult(
                chunk_id="a",
                document_id="doc-a",
                title="A",
                text="retrieval architecture hybrid search",
                source_path="a.txt",
                score=0.3,
                token_count=4,
            ),
            RetrievalResult(
                chunk_id="b",
                document_id="doc-b",
                title="B",
                text="travel and football notes",
                source_path="b.txt",
                score=0.31,
                token_count=4,
            ),
        ],
    )

    assert results[0].title == "A"


def test_semantic_reranker_uses_injected_scorer():
    class FakeScorer:
        def predict(self, pairs, batch_size=8, show_progress_bar=False):
            del batch_size, show_progress_bar
            assert pairs[0][0] == "retrieval architecture"
            return [0.91, 0.15]

    reranker = SemanticCrossEncoderReranker(top_k=1, scorer=FakeScorer())
    results = reranker.rank(
        "retrieval architecture",
        [
            RetrievalResult(
                chunk_id="a",
                document_id="doc-a",
                title="A",
                text="retrieval architecture hybrid search",
                source_path="a.txt",
                score=0.3,
                token_count=4,
            ),
            RetrievalResult(
                chunk_id="b",
                document_id="doc-b",
                title="B",
                text="travel and football notes",
                source_path="b.txt",
                score=0.31,
                token_count=4,
            ),
        ],
    )

    assert results[0].title == "B"


def test_context_builder_respects_token_budget_and_keeps_multiple_chunks_from_same_document():
    builder = ContextBuilder(max_chunks=3, max_tokens=9)
    prompt, selected = builder.build(
        query="What is the architecture?",
        candidates=[
            RetrievalResult(
                chunk_id="a1",
                document_id="doc-a",
                title="Architecture",
                text="one two three four",
                source_path="a.txt",
                score=1.0,
                token_count=4,
            ),
            RetrievalResult(
                chunk_id="a2",
                document_id="doc-a",
                title="Architecture",
                text="second section about architecture",
                source_path="a.txt",
                score=0.9,
                token_count=3,
            ),
            RetrievalResult(
                chunk_id="b1",
                document_id="doc-b",
                title="Notes",
                text="five six seven eight",
                source_path="b.txt",
                score=0.8,
                token_count=4,
            ),
        ],
    )

    assert len(selected) == 2
    assert "second section about architecture" in prompt


def test_context_builder_adds_characteristics_specific_guidance():
    builder = ContextBuilder(max_chunks=2, max_tokens=20)
    prompt, _ = builder.build(
        query="Tell me your characteristics",
        candidates=[
            RetrievalResult(
                chunk_id="profile::0",
                document_id="profile",
                title="Profile",
                text="Gaurav Kalita is a collaborative engineer.",
                source_path="profile.json",
                score=1.0,
                token_count=8,
            )
        ],
    )

    assert "characteristics, qualities, strengths, or traits" in prompt
    assert "Do not infer personality from job titles" in prompt


def test_query_processing_pipeline_expands_queries_and_extracts_metadata():
    pipeline = build_query_processing_pipeline()

    result = pipeline.process("What is the architecture of Digital Me?")

    assert result["normalized_query"] == "what is the architecture of digital me?"
    assert result["queries"]
    assert any("design system components" in query for query in result["queries"])
    assert result["metadata"]["type"] == "document"


class FakeProvider(BaseLLMProvider):
    async def generate(self, prompt: str) -> str:
        return "answer from provider"


class FailingProvider(BaseLLMProvider):
    async def generate(self, prompt: str) -> str:
        del prompt
        raise RuntimeError("provider unavailable")


class FakeRetriever:
    async def retrieve(self, queries):
        assert queries
        return [
            RetrievalResult(
                chunk_id="a",
                document_id="doc-a",
                title="Architecture",
                text="Digital Me uses a layered RAG architecture.",
                source_path="a.txt",
                score=1.0,
                token_count=7,
            )
        ]


class FakeCacheStore:
    def __init__(self):
        self.payloads = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str):
        self.get_calls += 1
        return self.payloads.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int):
        del ttl_seconds
        self.set_calls += 1
        self.payloads[key] = value

    async def delete(self, key: str):
        self.payloads.pop(key, None)


class FakeVectorStore:
    def __init__(self):
        self.search_calls = 0

    def load_chunks(self):
        return [1]

    def search(self, query_embedding, top_k):
        del query_embedding, top_k
        self.search_calls += 1
        return [
            RetrievalResult(
                chunk_id="cache::0",
                document_id="doc-cache",
                title="Cached result",
                text="cached retrieval payload",
                source_path="cache.txt",
                score=1.0,
                token_count=3,
            )
        ]


class FakeEmbedder:
    def embed(self, text: str):
        del text
        return [0.1, 0.2, 0.3]


def test_vector_repository_caches_retrieval_results():
    cache_store = FakeCacheStore()
    repository = VectorRepository(
        vector_store=FakeVectorStore(),
        embedder=FakeEmbedder(),
        cache_store=cache_store,
    )

    first = __import__("asyncio").run(repository.retrieve("Cache this query"))
    second = __import__("asyncio").run(repository.retrieve("Cache this query"))

    assert first[0].title == "Cached result"
    assert second[0].title == "Cached result"
    assert cache_store.set_calls == 1
    assert cache_store.get_calls == 2
    assert repository.vector_store.search_calls == 1


def test_rag_pipeline_uses_query_processing_pipeline_end_to_end():
    pipeline = RAGPipeline(
        query_processor=build_query_processing_pipeline(),
        provider=FakeProvider(),
        retriever=FakeRetriever(),
        reranker=HybridReranker(top_k=1),
        context_builder=ContextBuilder(max_chunks=1, max_tokens=20),
    )

    result = __import__("asyncio").run(pipeline.answer("What is the architecture of Digital Me?"))

    assert result.answer == "answer from provider"
    assert result.processed_query["queries"]
    assert result.context_items[0].title == "Architecture"


def test_rag_pipeline_falls_back_when_provider_fails():
    pipeline = RAGPipeline(
        query_processor=build_query_processing_pipeline(),
        provider=FailingProvider(),
        retriever=FakeRetriever(),
        reranker=HybridReranker(top_k=1),
        context_builder=ContextBuilder(max_chunks=1, max_tokens=20),
    )

    result = __import__("asyncio").run(pipeline.answer("What is the architecture of Digital Me?"))

    assert "generation provider is unavailable" in result.answer.lower()
