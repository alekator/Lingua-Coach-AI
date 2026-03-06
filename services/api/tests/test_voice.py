from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.models import LearnerProfile
from app.services.voice import default_voice_teacher


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

        progress = client.get("/voice/progress", params={"user_id": 77})
        assert progress.status_code == 200
        progress_body = progress.json()
        assert progress_body["user_id"] == 77
        assert progress_body["trend"] in {"stable", "improving", "declining"}
        assert "recommendation" in progress_body


def test_voice_message_uses_profile_target_lang_when_not_provided(
    client_factory: Callable[..., TestClient],
) -> None:
    chain: list[tuple[str, Any]] = []

    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        chain.append(("asr", (len(audio_bytes), filename, content_type, language_hint)))
        return {"transcript": "Ich lerne jeden Tag", "language": "de"}

    def fake_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        chain.append(("teacher", (transcript, target_lang, getattr(profile, "target_lang", None))))
        return "Coach reply in profile target language."

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        chain.append(("tts", (text, target_lang, voice_name)))
        return "http://tts.local/audio/profile-target.mp3"

    with client_factory(
        asr_transcriber=fake_asr,
        voice_teacher=fake_teacher,
        tts_synthesizer=fake_tts,
    ) as client:
        setup = client.post(
            "/profile/setup",
            json={
                "user_id": 88,
                "native_lang": "de",
                "target_lang": "fr",
                "level": "A2",
                "goal": "travel",
                "preferences": {},
            },
        )
        assert setup.status_code == 200

        response = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "88", "language_hint": "de", "voice_name": "alloy"},
        )
        assert response.status_code == 200
        assert response.json()["audio_url"] == "http://tts.local/audio/profile-target.mp3"

        teacher_step = next(step for step in chain if step[0] == "teacher")
        assert teacher_step[1][1] == "fr"
        tts_step = next(step for step in chain if step[0] == "tts")
        assert tts_step[1][1] == "fr"


def test_default_voice_teacher_fallback_respects_strictness(monkeypatch: Any) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profile = LearnerProfile(
        user_id=1,
        native_lang="ru",
        target_lang="en",
        level="A2",
        goal="travel",
        preferences={"strictness": "high"},
    )
    text = default_voice_teacher("I goed home", profile, "en")
    assert text.startswith("Straight feedback:")
    assert "went" in text


def test_voice_message_teacher_failure_uses_router_fallback(
    client_factory: Callable[..., TestClient],
) -> None:
    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        return {"transcript": "I goed to school", "language": "en"}

    def broken_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        raise RuntimeError("teacher unavailable")

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        return "http://tts.local/audio/fallback.mp3"

    with client_factory(
        asr_transcriber=fake_asr,
        voice_teacher=broken_teacher,
        tts_synthesizer=fake_tts,
    ) as client:
        response = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "77", "target_lang": "en", "language_hint": "en", "voice_name": "alloy"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["audio_url"] == "http://tts.local/audio/fallback.mp3"
        assert "Quick fallback coach in en" in body["teacher_text"]


def test_voice_message_budget_cap_blocks_paid_path(
    client_factory: Callable[..., TestClient],
) -> None:
    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        return {"transcript": "I goed to school", "language": "en"}

    def fake_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        return "You should say: I went to school."

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        return "http://tts.local/audio/voice-1.mp3"

    with client_factory(
        asr_transcriber=fake_asr,
        voice_teacher=fake_teacher,
        tts_synthesizer=fake_tts,
    ) as client:
        setup = client.post(
            "/profile/setup",
            json={
                "user_id": 79,
                "native_lang": "ru",
                "target_lang": "en",
                "level": "A2",
                "goal": "travel",
                "preferences": {},
            },
        )
        assert setup.status_code == 200
        cap_set = client.post(
            "/settings/usage-budget",
            json={"user_id": 79, "daily_token_cap": 1, "weekly_token_cap": 1, "warning_threshold": 0.8},
        )
        assert cap_set.status_code == 200

        first = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "79", "target_lang": "en", "language_hint": "en", "voice_name": "alloy"},
        )
        assert first.status_code == 200

        second = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "79", "target_lang": "en", "language_hint": "en", "voice_name": "alloy"},
        )
        assert second.status_code == 200
        body = second.json()
        assert body["audio_url"] == "offline://budget-blocked"
        assert "Budget cap reached" in body["teacher_text"]


def test_voice_message_tts_failure_keeps_response_in_light_mode(
    client_factory: Callable[..., TestClient],
) -> None:
    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        return {"transcript": "I goed to school", "language": "en"}

    def fake_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        return "You should say: I went to school."

    def broken_tts(text: str, target_lang: str, voice_name: str) -> str:
        raise RuntimeError("tts unavailable")

    with client_factory(
        asr_transcriber=fake_asr,
        voice_teacher=fake_teacher,
        tts_synthesizer=broken_tts,
    ) as client:
        response = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "77", "target_lang": "en", "language_hint": "en", "voice_name": "alloy"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["audio_url"] == "offline://tts-unavailable"
        assert "Audio playback is temporarily unavailable" in body["teacher_text"]


def test_voice_transcribe_rejects_invalid_language_hint(client: TestClient) -> None:
    response = client.post(
        "/voice/transcribe",
        files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
        data={"language_hint": "en!"},
    )
    assert response.status_code == 400
    assert "Invalid language code" in response.json()["detail"]


def test_voice_message_uses_language_limited_fallback_for_unsupported_speech(
    client_factory: Callable[..., TestClient],
) -> None:
    def fake_asr(audio_bytes: bytes, filename: str, content_type: str, language_hint: str) -> dict[str, str]:
        return {"transcript": "Test transcript", "language": "sv"}

    def fake_teacher(transcript: str, profile: Any, target_lang: str) -> str:
        return "Coach text."

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        raise RuntimeError("should not be called for unsupported language")

    with client_factory(
        asr_transcriber=fake_asr,
        voice_teacher=fake_teacher,
        tts_synthesizer=fake_tts,
    ) as client:
        response = client.post(
            "/voice/message",
            files={"file": ("voice.webm", b"voice-bytes", "audio/webm")},
            data={"user_id": "77", "target_lang": "sv", "language_hint": "sv", "voice_name": "alloy"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["audio_url"] == "offline://tts-language-limited"
        assert "Voice playback for this language is limited" in body["teacher_text"]
