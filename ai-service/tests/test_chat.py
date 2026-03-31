from fastapi.testclient import TestClient

from app.api.endpoints.chat import get_chat_service
from app.data_layer.models import RetrievalResult
from app.main import app
from app.rag.pipeline import RAGResult
from app.services.chat_service import ChatService

client = TestClient(app, raise_server_exceptions=False)


def test_health():
    resp = client.get("/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


class FakeLLM:
    def __init__(self, response: str = "Stub response", should_fail: bool = False):
        self.response = response
        self.should_fail = should_fail

    async def generate(self, prompt: str) -> str:
        if self.should_fail:
            raise RuntimeError("llm unavailable")
        return self.response


class FakeRAGPipeline:
    def __init__(self, docs, rewritten_query="Who are you?", prompt="Prompt"):
        self.docs = docs
        self.rewritten_query = rewritten_query
        self.prompt = prompt

    async def prepare(self, query: str):
        return RAGResult(
            prompt=self.prompt,
            context_items=self.docs,
            processed_query={
                "original_query": query,
                "normalized_query": query,
                "rewritten_query": self.rewritten_query,
                "metadata": {},
            },
        )


def override_chat_service_with(service: ChatService):
    app.dependency_overrides[get_chat_service] = lambda: service


def clear_overrides():
    app.dependency_overrides.clear()


def test_chat_returns_answer_with_sources():
    service = ChatService(
        rag_pipeline=FakeRAGPipeline(
            [
                RetrievalResult(
                    chunk_id="profile::0",
                    document_id="profile",
                    title="Profile",
                    text="Memory one",
                    source_path="profile.json",
                    score=1.0,
                    token_count=20,
                ),
                RetrievalResult(
                    chunk_id="notes::0",
                    document_id="notes",
                    title="Notes",
                    text="Memory two",
                    source_path="notes.md",
                    score=0.8,
                    token_count=18,
                ),
            ]
        ),
        llm=FakeLLM("Personalized answer"),
    )
    override_chat_service_with(service)

    resp = client.post("/chat/", json={"question": "Who are you?"})

    clear_overrides()
    assert resp.status_code == 200
    assert resp.json() == {
        "answer": "Personalized answer",
        "sources": ["Profile", "Notes"],
        "query": "Who are you?",
    }


def test_chat_returns_fallback_when_no_documents():
    service = ChatService(
        rag_pipeline=FakeRAGPipeline([], rewritten_query="Tell me about my past."),
        llm=FakeLLM("Unused"),
    )
    override_chat_service_with(service)

    resp = client.post("/chat/", json={"question": "Tell me about my past."})

    clear_overrides()
    assert resp.status_code == 200
    assert resp.json() == {
        "answer": "I don't have enough information to answer that yet.",
        "sources": [],
        "query": "Tell me about my past.",
    }


def test_chat_returns_error_when_llm_fails():
    service = ChatService(
        rag_pipeline=FakeRAGPipeline(
            [
                RetrievalResult(
                    chunk_id="profile::0",
                    document_id="profile",
                    title="Profile",
                    text="Memory",
                    source_path="profile.json",
                    score=1.0,
                    token_count=20,
                )
            ]
        ),
        llm=FakeLLM(should_fail=True),
    )
    override_chat_service_with(service)

    resp = client.post("/chat/", json={"question": "Say something smart"})

    clear_overrides()
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Failed to process request"}
