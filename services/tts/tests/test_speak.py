from fastapi.testclient import TestClient

from app.main import create_app


def test_tts_speak_requires_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())
    response = client.post(
        "/tts/speak",
        json={"text": "Hello", "language": "en", "voice": "alloy"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY is not configured for TTS"


def test_tts_speak_returns_audio_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TTS_AUDIO_DIR", str(tmp_path))

    class FakeSpeechResponse:
        def read(self) -> bytes:
            return b"fake-mp3"

    class FakeOpenAI:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.audio = self
            self.speech = self

        def create(self, **kwargs):
            assert kwargs["model"]
            assert kwargs["voice"] == "alloy"
            assert kwargs["input"] == "Hello"
            return FakeSpeechResponse()

    monkeypatch.setattr("app.main.OpenAI", FakeOpenAI)

    client = TestClient(create_app())
    response = client.post(
        "/tts/speak",
        json={"text": "Hello", "language": "en", "voice": "alloy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["audio_url"].startswith("/audio/alloy-")
    assert body["mime_type"] == "audio/mpeg"

    download = client.get(body["audio_url"])
    assert download.status_code == 200
    assert download.content == b"fake-mp3"


def test_tts_speak_prefers_header_key_over_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("TTS_AUDIO_DIR", str(tmp_path))
    captured: dict[str, str] = {}

    class FakeSpeechResponse:
        def read(self) -> bytes:
            return b"fake-mp3"

    class FakeOpenAI:
        def __init__(self, api_key: str) -> None:
            captured["api_key"] = api_key
            self.audio = self
            self.speech = self

        def create(self, **kwargs):
            return FakeSpeechResponse()

    monkeypatch.setattr("app.main.OpenAI", FakeOpenAI)

    client = TestClient(create_app())
    response = client.post(
        "/tts/speak",
        json={"text": "Hello", "language": "en", "voice": "alloy"},
        headers={"X-OpenAI-API-Key": "header-key"},
    )

    assert response.status_code == 200
    assert response.json()["audio_url"].startswith("/audio/alloy-")
    assert captured["api_key"] == "header-key"


def test_tts_speak_local_provider_returns_wav(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "local")
    monkeypatch.setenv("TTS_AUDIO_DIR", str(tmp_path))
    monkeypatch.setenv("LOCAL_TTS_MODEL_PATH", "F:/models/qwen3-tts")

    def fake_local_speech(text: str, language: str, voice: str) -> bytes:
        assert text == "Hello local"
        assert language == "en"
        assert voice == "alloy"
        return b"RIFF....WAVE"

    monkeypatch.setattr("app.main._synthesize_local_speech", fake_local_speech)

    client = TestClient(create_app())
    response = client.post(
        "/tts/speak",
        json={"text": "Hello local", "language": "en", "voice": "alloy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["audio_url"].startswith("/audio/alloy-")
    assert body["audio_url"].endswith(".wav")
    assert body["mime_type"] == "audio/wav"

    download = client.get(body["audio_url"])
    assert download.status_code == 200


def test_tts_provider_endpoints() -> None:
    client = TestClient(create_app())
    set_resp = client.post("/tts/provider", json={"provider": "local"})
    assert set_resp.status_code == 200
    assert set_resp.json()["provider"] == "local"

    get_resp = client.get("/tts/provider")
    assert get_resp.status_code == 200
    assert get_resp.json()["provider"] == "local"


def test_tts_diagnostics_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "openai")
    client = TestClient(create_app())
    response = client.get("/tts/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai"
    assert body["status"] == "disabled"
