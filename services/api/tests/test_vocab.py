from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.services import vocab_ai as vocab_ai_service


def test_vocab_add_and_list(client: TestClient) -> None:
    added = client.post(
        "/vocab/add",
        json={
            "user_id": 501,
            "word": "achieve",
            "translation": "to achieve",
            "example": "I want to achieve my goals.",
        },
    )
    assert added.status_code == 200
    body = added.json()
    assert body["word"] == "achieve"
    assert body["interval_days"] == 1
    assert body["ease"] == 2.5

    listing = client.get("/vocab", params={"user_id": 501})
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["word"] == "achieve"


def test_vocab_review_next_and_submit(client: TestClient) -> None:
    added = client.post(
        "/vocab/add",
        json={
            "user_id": 777,
            "word": "mistake",
            "translation": "error",
        },
    )
    vocab_item_id = added.json()["id"]

    first_next = client.post("/vocab/review/next", json={"user_id": 777})
    assert first_next.status_code == 200
    next_payload = first_next.json()
    assert next_payload["has_item"] is True
    assert next_payload["item"]["id"] == vocab_item_id

    submit = client.post(
        "/vocab/review/submit",
        json={"user_id": 777, "vocab_item_id": vocab_item_id, "rating": "good"},
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["interval_days"] >= 2
    assert submit_payload["ease"] >= 2.5


def test_vocab_add_enriches_with_openai_provider(client: TestClient, monkeypatch) -> None:
    calls: dict[str, Any] = {}

    class FakeResponse:
        output_text = (
            '{"translation":"добиваться",'
            '"example":"I want to achieve this goal by June.",'
            '"phonetics":"əˈtʃiːv"}'
        )

    class FakeResponsesApi:
        def create(self, **kwargs):
            calls["kwargs"] = kwargs
            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, api_key: str):
            calls["api_key"] = api_key
            self.responses = FakeResponsesApi()

    monkeypatch.setenv("API_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-vocab")
    monkeypatch.setattr(vocab_ai_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(vocab_ai_service, "usage_from_response", lambda _response: {"total_tokens": 10})
    monkeypatch.setattr(vocab_ai_service, "log_usage", lambda *_args, **_kwargs: None)

    added = client.post(
        "/vocab/add",
        json={
            "user_id": 930,
            "word": "achieve",
            "translation": "to achieve",
        },
    )
    assert added.status_code == 200
    body = added.json()
    assert body["translation"] == "добиваться"
    assert body["example"] == "I want to achieve this goal by June."
    assert body["phonetics"] == "əˈtʃiːv"
    assert body["enrichment_source"] == "openai"
    assert calls["api_key"] == "sk-test-vocab"
    assert calls["kwargs"]["model"]


def test_vocab_add_enriches_with_local_provider(client: TestClient, monkeypatch) -> None:
    calls: dict[str, Any] = {}

    def fake_complete_json(
        system_prompt: str,
        messages: list[dict[str, str]],
        max_output_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        calls["system_prompt"] = system_prompt
        calls["messages"] = messages
        calls["max_output_tokens"] = max_output_tokens
        calls["temperature"] = temperature
        return {
            "translation": "добиваться",
            "example": "She can achieve better results with practice.",
            "phonetics": "əˈtʃiːv",
        }

    monkeypatch.setenv("API_LLM_PROVIDER", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(vocab_ai_service, "complete_json", fake_complete_json)

    added = client.post(
        "/vocab/add",
        json={
            "user_id": 931,
            "word": "achieve",
            "translation": "to achieve",
        },
    )
    assert added.status_code == 200
    body = added.json()
    assert body["translation"] == "добиваться"
    assert body["example"] == "She can achieve better results with practice."
    assert body["phonetics"] == "əˈtʃiːv"
    assert body["enrichment_source"] == "local"
    assert calls["messages"][0]["content"]
    assert calls["max_output_tokens"] > 0
