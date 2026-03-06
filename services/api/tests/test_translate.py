from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient


def test_translate_without_voice(
    client_factory: Callable[..., TestClient],
) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_translator(text: str, source_lang: str, target_lang: str) -> str:
        calls.append((text, source_lang, target_lang))
        return "Hola mundo"

    with client_factory(translator=fake_translator) as client:
        response = client.post(
            "/translate",
            json={
                "text": "Hello world",
                "source_lang": "en",
                "target_lang": "es",
                "voice": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["translated_text"] == "Hola mundo"
        assert body["audio_url"] is None
        assert calls == [("Hello world", "en", "es")]


def test_translate_with_voice_uses_tts(
    client_factory: Callable[..., TestClient],
) -> None:
    translator_calls: list[tuple[str, str, str]] = []
    tts_calls: list[tuple[str, str, str]] = []

    def fake_translator(text: str, source_lang: str, target_lang: str) -> str:
        translator_calls.append((text, source_lang, target_lang))
        return "Bonjour"

    def fake_tts(text: str, target_lang: str, voice_name: str) -> str:
        tts_calls.append((text, target_lang, voice_name))
        return "http://tts.local/audio/abc123.mp3"

    with client_factory(translator=fake_translator, tts_synthesizer=fake_tts) as client:
        response = client.post(
            "/translate",
            json={
                "text": "Good day",
                "source_lang": "en",
                "target_lang": "fr",
                "voice": True,
                "voice_name": "alloy",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["translated_text"] == "Bonjour"
        assert body["audio_url"] == "http://tts.local/audio/abc123.mp3"
        assert translator_calls == [("Good day", "en", "fr")]
        assert tts_calls == [("Bonjour", "fr", "alloy")]


def test_translate_same_language_short_circuit(client: TestClient) -> None:
    response = client.post(
        "/translate",
        json={
            "text": "Hello world",
            "source_lang": "en",
            "target_lang": "en",
            "voice": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["translated_text"] == "Hello world"


def test_translate_budget_cap_returns_lightweight_mode(
    client_factory: Callable[..., TestClient],
) -> None:
    def fake_translator(text: str, source_lang: str, target_lang: str) -> str:
        return "Hola mundo"

    with client_factory(translator=fake_translator) as client:
        setup = client.post(
            "/profile/setup",
            json={
                "user_id": 80,
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
            json={"user_id": 80, "daily_token_cap": 1, "weekly_token_cap": 1, "warning_threshold": 0.8},
        )
        assert cap_set.status_code == 200

        first = client.post(
            "/translate",
            json={"user_id": 80, "text": "Hello world", "source_lang": "en", "target_lang": "es", "voice": False},
        )
        assert first.status_code == 200
        assert first.json()["translated_text"] == "Hola mundo"

        second = client.post(
            "/translate",
            json={"user_id": 80, "text": "Second phrase", "source_lang": "en", "target_lang": "es", "voice": False},
        )
        assert second.status_code == 200
        assert second.json()["translated_text"] == "Second phrase"


def test_translate_provider_failure_uses_lightweight_fallback(
    client_factory: Callable[..., TestClient],
) -> None:
    def broken_translator(text: str, source_lang: str, target_lang: str) -> str:
        raise RuntimeError("provider down")

    with client_factory(translator=broken_translator) as client:
        response = client.post(
            "/translate",
            json={
                "text": "Good evening",
                "source_lang": "en",
                "target_lang": "de",
                "voice": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["translated_text"] == "[en->de] Good evening"


def test_translate_tts_failure_returns_text_without_audio(
    client_factory: Callable[..., TestClient],
) -> None:
    def fake_translator(text: str, source_lang: str, target_lang: str) -> str:
        return "Guten Abend"

    def broken_tts(text: str, target_lang: str, voice_name: str) -> str:
        raise RuntimeError("tts unavailable")

    with client_factory(translator=fake_translator, tts_synthesizer=broken_tts) as client:
        response = client.post(
            "/translate",
            json={
                "text": "Good evening",
                "source_lang": "en",
                "target_lang": "de",
                "voice": True,
                "voice_name": "alloy",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["translated_text"] == "Guten Abend"
        assert body["audio_url"] is None
