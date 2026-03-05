from fastapi.testclient import TestClient

from app.main import create_app


def test_asr_transcribe_stub() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/asr/transcribe",
        files={"file": ("sample.webm", b"fake-bytes", "audio/webm")},
        data={"language_hint": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert "sample.webm" in body["transcript"]
