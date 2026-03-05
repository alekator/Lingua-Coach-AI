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
