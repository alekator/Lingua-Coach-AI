from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import create_app
from app.schemas.chat import ChatMessageResponse


@pytest.fixture(autouse=True)
def isolate_runtime_ai_env() -> Generator[None, None, None]:
    previous_openai_key = os.environ.get("OPENAI_API_KEY")
    previous_llm_provider = os.environ.get("API_LLM_PROVIDER")
    os.environ["OPENAI_API_KEY"] = "sk-test-suite"
    os.environ["API_LLM_PROVIDER"] = os.environ.get("API_LLM_PROVIDER", "openai")
    try:
        yield
    finally:
        if previous_openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = previous_openai_key
        if previous_llm_provider is None:
            os.environ.pop("API_LLM_PROVIDER", None)
        else:
            os.environ["API_LLM_PROVIDER"] = previous_llm_provider


@pytest.fixture()
def client_factory() -> Callable[..., TestClient]:
    def _build(
        teacher_responder: Callable[[dict[str, Any]], ChatMessageResponse] | None = None,
        translator: Callable[[str, str, str], str] | None = None,
        tts_synthesizer: Callable[[str, str, str], str] | None = None,
        asr_transcriber: Callable[[bytes, str, str, str], dict[str, str]] | None = None,
        voice_teacher: Callable[[str, Any, str], str] | None = None,
    ) -> TestClient:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        testing_session_local = sessionmaker(
            bind=engine, autocommit=False, autoflush=False, class_=Session
        )
        Base.metadata.create_all(bind=engine)

        def override_get_db() -> Generator[Session, None, None]:
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        app = create_app(
            teacher_responder=teacher_responder,
            translator=translator,
            tts_synthesizer=tts_synthesizer,
            asr_transcriber=asr_transcriber,
            voice_teacher=voice_teacher,
        )
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app)

    return _build


@pytest.fixture()
def client(client_factory: Callable[..., TestClient]) -> Generator[TestClient, None, None]:
    with client_factory() as test_client:
        yield test_client
