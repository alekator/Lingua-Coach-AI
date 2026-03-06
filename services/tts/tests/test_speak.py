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
