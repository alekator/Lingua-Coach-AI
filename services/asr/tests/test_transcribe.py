from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import AsrTranscribeResponse, create_app


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


def test_asr_transcribe_prefers_header_key_over_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    captured: dict[str, str] = {}

    class FakeTranscript:
        text = "hello from provider"
        language = "en"

    class FakeOpenAI:
        def __init__(self, api_key: str) -> None:
            captured["api_key"] = api_key
            self.audio = self
            self.transcriptions = self

        def create(self, **kwargs):
            return FakeTranscript()

    monkeypatch.setattr("app.main.OpenAI", FakeOpenAI)

    client = TestClient(create_app())
    response = client.post(
        "/asr/transcribe",
        files={"file": ("sample.webm", b"fake-bytes", "audio/webm")},
        data={"language_hint": "en"},
        headers={"X-OpenAI-API-Key": "header-key"},
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "hello from provider"
    assert captured["api_key"] == "header-key"


def test_asr_transcribe_local_provider_path(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "local")

    def fake_local_transcribe(file, language_hint: str) -> AsrTranscribeResponse:
        assert language_hint == "auto"
        return AsrTranscribeResponse(transcript="hello from local asr", language="en")

    monkeypatch.setattr("app.main.local_transcribe", fake_local_transcribe)

    client = TestClient(create_app())
    response = client.post(
        "/asr/transcribe",
        files={"file": ("sample.webm", b"fake-bytes", "audio/webm")},
        data={"language_hint": "auto"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["transcript"] == "hello from local asr"


def test_asr_provider_endpoints() -> None:
    client = TestClient(create_app())
    set_resp = client.post("/asr/provider", json={"provider": "local"})
    assert set_resp.status_code == 200
    assert set_resp.json()["provider"] == "local"

    get_resp = client.get("/asr/provider")
    assert get_resp.status_code == 200
    assert get_resp.json()["provider"] == "local"


def test_asr_diagnostics_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "openai")
    client = TestClient(create_app())
    response = client.get("/asr/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai"
    assert body["status"] == "disabled"


def test_asr_diagnostics_local_formats_error_without_500(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ASR_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_ASR_MODEL_PATH", str(tmp_path))
    monkeypatch.setattr(
        "app.main._get_local_asr_model",
        lambda: (_ for _ in ()).throw(HTTPException(status_code=503, detail="custom local asr failure")),
    )
    client = TestClient(create_app())
    response = client.get("/asr/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "custom local asr failure" in body["message"]
    assert "backend: transformers-whisper" in body["message"]
