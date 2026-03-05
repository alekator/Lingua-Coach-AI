from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    database_url: str = "sqlite:///./linguacoach.db"
    asr_url: str = "http://asr:8001"
    tts_url: str = "http://tts:8002"

    # Cost-aware OpenAI defaults.
    openai_chat_model: str = "gpt-4.1-mini"
    openai_voice_model: str = "gpt-4.1-mini"
    openai_translate_model: str = "gpt-4.1-mini"
    openai_asr_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"

    openai_chat_max_output_tokens: int = 320
    openai_voice_max_output_tokens: int = 180
    openai_translate_max_output_tokens: int = 180

    openai_temperature_chat: float = 0.4
    openai_temperature_voice: float = 0.3
    openai_temperature_translate: float = 0.0

    ai_cache_max_items: int = 512


settings = Settings()
