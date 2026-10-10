from fastapi.testclient import TestClient

from app.api.endpoints.forms import build_form_fill_use_case
from app.application.form_filling.dto import FormFieldDescriptor, FormFillCommand
from app.application.form_filling.use_cases import DefaultPlanFormFillUseCase
from app.data_layer.models import RetrievalResult
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


class FakeQueryProcessor:
    def process(self, query: str):
        return {
            "original_query": query,
            "normalized_query": query.lower(),
            "rewritten_query": query,
            "queries": [query],
        }


class FakeRetriever:
    async def retrieve(self, queries):
        del queries
        return [
            RetrievalResult(
                chunk_id="profile::0",
                document_id="profile",
                title="Gaurav Kalita Profile",
                text="Gaurav Kalita is a full-stack engineer. Notice period is 1 month.",
                source_path="profile.json",
                score=1.0,
                token_count=20,
                metadata={"category": "identity"},
            )
        ]


class FakeReranker:
    def rank(self, query: str, candidates):
        del query
        return list(candidates)


class FakeProvider:
    async def generate(self, prompt: str) -> str:
        del prompt
        return (
            "{"
            '"site":"naukri",'
            '"page_url":"https://www.naukri.com",'
            '"actions":['
            '{"field_id":"full_name","action":"fill","value":"Gaurav Kalita","confidence":0.99,"risk":"low","reason":"Profile name","source_labels":["Gaurav Kalita Profile"],"matched_field":"preferred_name"},'
            '{"field_id":"notice_period","action":"fill","value":"1 month","confidence":0.96,"risk":"medium","reason":"Availability is grounded in profile data","source_labels":["Gaurav Kalita Profile"],"matched_field":"availability.notice_period"}'
            "]}"
        )


def _build_use_case() -> DefaultPlanFormFillUseCase:
    return DefaultPlanFormFillUseCase(
        query_processor=FakeQueryProcessor(),
        retriever=FakeRetriever(),
        reranker=FakeReranker(),
        context_builder=__import__("app.rag.context_builder", fromlist=["ContextBuilder"]).ContextBuilder(max_chunks=3, max_tokens=100),
        provider=FakeProvider(),
    )


def test_form_fill_use_case_generates_structured_actions():
    use_case = _build_use_case()
    command = FormFillCommand(
        site="naukri",
        page_url="https://www.naukri.com",
        page_title="Profile",
        fields=[
            FormFieldDescriptor(
                field_id="full_name",
                label="Full Name",
                field_type="text",
                tag_name="input",
            ),
            FormFieldDescriptor(
                field_id="notice_period",
                label="Notice Period",
                field_type="text",
                tag_name="input",
            ),
        ],
    )

    result = __import__("asyncio").run(use_case.execute(command))

    assert result.site == "naukri"
    assert len(result.actions) == 2
    assert result.actions[0].field_id == "full_name"
    assert result.actions[0].value == "Gaurav Kalita"


def test_form_fill_endpoint_returns_plan():
    app.dependency_overrides[build_form_fill_use_case] = _build_use_case

    resp = client.post(
        "/forms/plan",
        json={
            "site": "naukri",
            "page_url": "https://www.naukri.com",
            "page_title": "Profile",
            "fields": [
                {
                    "field_id": "full_name",
                    "label": "Full Name",
                    "field_type": "text",
                    "tag_name": "input",
                }
            ],
        },
    )

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["site"] == "naukri"
    assert payload["actions"][0]["value"] == "Gaurav Kalita"

