from __future__ import annotations

from pydantic import BaseModel, Field


class OpenAIKeySetRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=512)


class OpenAIKeyStatusResponse(BaseModel):
    configured: bool
    source: str
    masked: str | None = None
    persistent: bool = False
    secure_storage: bool = False


class UsageBudgetSetRequest(BaseModel):
    user_id: int = Field(ge=1)
    daily_token_cap: int = Field(default=12000, ge=0, le=2_000_000)
    weekly_token_cap: int = Field(default=60000, ge=0, le=10_000_000)
    warning_threshold: float = Field(default=0.8, ge=0.5, le=0.95)


class UsageBudgetStatusResponse(BaseModel):
    user_id: int
    daily_token_cap: int
    weekly_token_cap: int
    warning_threshold: float
    daily_used_tokens: int
    weekly_used_tokens: int
    daily_remaining_tokens: int
    weekly_remaining_tokens: int
    daily_warning: bool
    weekly_warning: bool
    blocked: bool


class LanguageCapabilitiesResponse(BaseModel):
    native_lang: str
    target_lang: str
    text_supported: bool
    asr_supported: bool
    tts_supported: bool
    voice_supported: bool
    recommendation: str


class AIRuntimeSetRequest(BaseModel):
    llm_provider: str = Field(default="openai", pattern="^(openai|local)$")
    asr_provider: str = Field(default="openai", pattern="^(openai|local)$")
    tts_provider: str = Field(default="openai", pattern="^(openai|local)$")


class AIModuleDiagnostics(BaseModel):
    provider: str
    status: str
    message: str
    model_path: str | None = None
    model_exists: bool = False
    dependency_available: bool = True
    device: str | None = None
    load_ms: float | None = None
    probe_ms: float | None = None


class AIRuntimeStatusResponse(BaseModel):
    llm_provider: str
    asr_provider: str
    tts_provider: str
    llm: AIModuleDiagnostics
    asr: AIModuleDiagnostics
    tts: AIModuleDiagnostics
