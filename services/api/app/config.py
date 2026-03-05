from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    database_url: str = "sqlite:///./linguacoach.db"
    asr_url: str = "http://asr:8001"
    tts_url: str = "http://tts:8002"


settings = Settings()
