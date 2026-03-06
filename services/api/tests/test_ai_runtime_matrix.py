from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.chat import ChatMessageResponse
from app.services.translate import default_tts_synthesizer
from app.services.voice import default_asr_transcriber


def test_openai_key_placeholder_is_treated_as_not_configured(client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "sk-...")
    response = client.get("/settings/openai-key")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["source"] == "none"


def test_default_asr_transcriber_sends_runtime_key_header(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890")
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"transcript": "hello", "language": "en"}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url: str, files: dict[str, Any], data: dict[str, Any], headers: dict[str, str]):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr("app.services.voice.httpx.Client", lambda timeout=25.0: FakeClient())
    result = default_asr_transcriber(b"bytes", "sample.webm", "audio/webm", "en")
    assert result["transcript"] == "hello"
    assert captured["url"].endswith("/asr/transcribe")
    assert captured["headers"]["X-OpenAI-API-Key"] == "sk-test-1234567890"


def test_default_tts_synthesizer_sends_runtime_key_header(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890")
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"audio_url": "/audio/demo.mp3"}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url: str, json: dict[str, Any], headers: dict[str, str]):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr("app.services.translate.httpx.Client", lambda timeout=20.0: FakeClient())
    audio_url = default_tts_synthesizer("Hello", "en", "alloy")
    assert audio_url == "/audio/demo.mp3"
    assert captured["url"].endswith("/tts/speak")
    assert captured["headers"]["X-OpenAI-API-Key"] == "sk-test-1234567890"
    assert captured["payload"]["voice"] == "alloy"


@pytest.mark.parametrize("provider", ["openai", "local"])
def test_ai_core_scenarios_work_for_openai_and_local_modes(
    client_factory: Callable[..., TestClient],
    monkeypatch,
    provider: str,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("API_LLM_PROVIDER", provider)
    monkeypatch.setenv("ASR_PROVIDER", provider)
    monkeypatch.setenv("TTS_PROVIDER", provider)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890")

    def fake_remote_diag(url: str, provider: str, fallback_message: str, run_probe: bool):
        return {
            "provider": provider,
            "status": "ok" if provider == "local" else "disabled",
            "message": "ready" if provider == "local" else "provider is OpenAI",
            "model_path": None,
            "model_exists": False,
            "dependency_available": True,
            "device": "cpu",
            "load_ms": 0.5,
            "probe_ms": 0.2 if run_probe else None,
        }

    def fake_llm_diag(run_probe: bool = False):
        if provider == "local":
            return {
                "provider": "local",
                "status": "ok",
                "message": "ready",
                "model_path": "/models/qwen2.5.gguf",
                "model_exists": True,
                "dependency_available": True,
                "device": "cpu",
                "load_ms": 1.0,
                "probe_ms": 0.3 if run_probe else None,
            }
        return {
            "provider": "openai",
            "status": "disabled",
            "message": "LLM provider is OpenAI",
            "model_path": None,
            "model_exists": False,
            "dependency_available": True,
            "device": "cpu",
            "load_ms": None,
            "probe_ms": None,
        }

    monkeypatch.setattr("app.routers.settings._fetch_remote_diag", fake_remote_diag)
    monkeypatch.setattr("app.routers.settings.get_local_llm_diagnostics", fake_llm_diag)

    def fake_teacher(_: dict[str, Any]) -> ChatMessageResponse:
        return ChatMessageResponse(assistant_text=f"{provider} chat reply")

    def fake_asr(audio: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        return {"transcript": f"{provider} transcript", "language": "en"}

    def fake_voice_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        return f"{provider} voice feedback: {transcript}"

    def fake_translator(text: str, source_lang: str, target_lang: str) -> str:
        return f"{provider} translated: {text}"

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        return f"http://tts.local/{provider}/{voice_name}.mp3"

    with client_factory(
        teacher_responder=fake_teacher,
        translator=fake_translator,
        tts_synthesizer=fake_tts,
        asr_transcriber=fake_asr,
        voice_teacher=fake_voice_teacher,
    ) as client:
        setup = client.post(
            "/profile/setup",
            json={
                "user_id": 910,
                "native_lang": "de",
                "target_lang": "en",
                "level": "A2",
                "goal": "travel",
                "preferences": {},
            },
        )
        assert setup.status_code == 200
        user_id = setup.json()["user_id"]

        runtime_set = client.post(
            "/settings/ai-runtime",
            json={"llm_provider": provider, "asr_provider": provider, "tts_provider": provider},
        )
        assert runtime_set.status_code == 200
        assert runtime_set.json()["llm_provider"] == provider
        assert runtime_set.json()["asr_provider"] == provider
        assert runtime_set.json()["tts_provider"] == provider

        runtime_status = client.get("/settings/ai-runtime", params={"probe": True})
        assert runtime_status.status_code == 200
        runtime_body = runtime_status.json()
        assert runtime_body["llm_provider"] == provider
        assert runtime_body["asr_provider"] == provider
        assert runtime_body["tts_provider"] == provider

        started = client.post("/chat/start", json={"user_id": user_id, "mode": "chat"})
        assert started.status_code == 200
        session_id = started.json()["session_id"]

        message = client.post("/chat/message", json={"session_id": session_id, "text": "hello coach"})
        assert message.status_code == 200
        assert provider in message.json()["assistant_text"]

        ended = client.post("/chat/end", json={"session_id": session_id})
        assert ended.status_code == 200

        voice = client.post(
            "/voice/message",
            files={"file": ("sample.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": str(user_id), "target_lang": "en", "language_hint": "en", "voice_name": "alloy"},
        )
        assert voice.status_code == 200
        assert voice.json()["transcript"] == f"{provider} transcript"
        assert voice.json()["audio_url"].endswith(".mp3")

        translate_text = client.post(
            "/translate",
            json={
                "user_id": user_id,
                "text": "hello world",
                "source_lang": "en",
                "target_lang": "de",
                "voice": True,
                "voice_name": "alloy",
            },
        )
        assert translate_text.status_code == 200
        assert provider in translate_text.json()["translated_text"]
        assert translate_text.json()["audio_url"].endswith(".mp3")

        translate_voice = client.post(
            "/translate/voice",
            files={"file": ("sample.webm", b"voice-bytes", "audio/webm")},
            data={"source_lang": "en", "target_lang": "de", "language_hint": "en", "voice_name": "alloy"},
        )
        assert translate_voice.status_code == 200
        body = translate_voice.json()
        assert body["transcript"] == f"{provider} transcript"
        assert provider in body["translated_text"]
        assert body["audio_url"].endswith(".mp3")
