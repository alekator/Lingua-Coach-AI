from fastapi import FastAPI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    status: str


class TtsSpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", min_length=2, max_length=32)
    voice: str = Field(default="alloy", min_length=2, max_length=32)


class TtsSpeakResponse(BaseModel):
    audio_url: str
    mime_type: str = "audio/mpeg"


def create_app() -> FastAPI:
    app = FastAPI(title="LinguaCoach TTS", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="tts", status="ok")

    @app.post("/tts/speak", response_model=TtsSpeakResponse)
    def tts_speak(payload: TtsSpeakRequest) -> TtsSpeakResponse:
        digest = abs(hash((payload.text, payload.language, payload.voice))) % 10_000_000
        return TtsSpeakResponse(audio_url=f"/audio/{payload.voice}-{digest}.mp3")

    return app


app = create_app()
