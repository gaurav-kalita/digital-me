from app.data_layer.models import RetrievalResult
from app.rag.contextBuilder import ContextBuilder
from app.rag.reranker import HybridReranker


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


def test_context_builder_respects_token_budget_and_deduplicates_documents():
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
                text="duplicate doc chunk",
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
    assert "duplicate doc chunk" not in prompt
