from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str


def create_app() -> FastAPI:
    app = FastAPI(title="LinguaCoach ASR", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="asr", status="ok")

    return app


app = create_app()
