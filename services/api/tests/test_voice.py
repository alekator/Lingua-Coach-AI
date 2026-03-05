from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient


def test_voice_transcribe_proxy(
    client_factory: Callable[..., TestClient],
) -> None:
    calls: list[tuple[int, str, str, str]] = []

    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        calls.append((len(audio_bytes), filename, content_type, language_hint))
        return {"transcript": "hello from asr", "language": "en"}

    with client_factory(asr_transcriber=fake_asr) as client:
        response = client.post(
            "/voice/transcribe",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"language_hint": "en"},
        )
        assert response.status_code == 200
        assert response.json() == {"transcript": "hello from asr", "language": "en"}
        assert calls == [(11, "voice.webm", "audio/webm", "en")]


def test_voice_message_pipeline(
    client_factory: Callable[..., TestClient],
) -> None:
    chain: list[tuple[str, Any]] = []

    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        chain.append(("asr", (len(audio_bytes), filename, content_type, language_hint)))
        return {"transcript": "I goed to school", "language": "en"}

    def fake_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        chain.append(("teacher", (transcript, target_lang, getattr(profile, "level", None))))
        return "You should say: I went to school."

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        chain.append(("tts", (text, target_lang, voice_name)))
        return "http://tts.local/audio/voice-1.mp3"

    with client_factory(
        asr_transcriber=fake_asr,
        voice_teacher=fake_teacher,
        tts_synthesizer=fake_tts,
    ) as client:
        client.post(
            "/profile/setup",
            json={
                "user_id": 77,
                "native_lang": "ru",
                "target_lang": "en",
                "level": "A2",
                "goal": "travel",
                "preferences": {},
            },
        )
        response = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "77", "target_lang": "en", "language_hint": "en", "voice_name": "alloy"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["transcript"] == "I goed to school"
        assert body["teacher_text"] == "You should say: I went to school."
        assert body["audio_url"] == "http://tts.local/audio/voice-1.mp3"
        assert len(body["pronunciation_feedback"]) > 10
        assert body["pronunciation_rubric"]["grammar_accuracy"] < 60
        assert body["pronunciation_rubric"]["level_band"] in {"needs_work", "developing", "solid"}
        assert len(body["pronunciation_rubric"]["actionable_tips"]) >= 1
        assert [step for step, _ in chain] == ["asr", "teacher", "tts"]
