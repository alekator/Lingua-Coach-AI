from fastapi.testclient import TestClient

from app.main import create_app


def test_tts_speak_returns_audio_url() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/tts/speak",
        json={"text": "Hello", "language": "en", "voice": "alloy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["audio_url"].startswith("/audio/alloy-")
    assert body["mime_type"] == "audio/mpeg"
