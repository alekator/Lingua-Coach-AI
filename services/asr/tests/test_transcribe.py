from fastapi.testclient import TestClient

from app.main import create_app


def test_asr_transcribe_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())
    response = client.post(
        "/asr/transcribe",
        files={"file": ("sample.webm", b"fake-bytes", "audio/webm")},
        data={"language_hint": "en"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY is not configured for ASR"


def test_asr_transcribe_calls_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeTranscript:
        text = "hello from provider"
        language = "en"

    class FakeOpenAI:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.audio = self
            self.transcriptions = self

        def create(self, **kwargs):
            assert kwargs["model"]
            assert kwargs["language"] == "en"
            return FakeTranscript()

    monkeypatch.setattr("app.main.OpenAI", FakeOpenAI)

    client = TestClient(create_app())
    response = client.post(
        "/asr/transcribe",
        files={"file": ("sample.webm", b"fake-bytes", "audio/webm")},
        data={"language_hint": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["transcript"] == "hello from provider"
