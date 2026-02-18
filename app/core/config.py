from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Interview Backend"
    api_prefix: str = "/api"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_transcribe_model: str = "gpt-4o-mini-transcribe"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "alloy"
    openai_tts_format: str = "mp3"

    database_url: str = "sqlite:////tmp/interview.db"

    @property
    def is_production(self) -> bool:
        return not self.database_url.startswith("sqlite")


settings = Settings()

# Log configuration on startup
import os
print("[config] Environment variables:")
print(f"  DATABASE_URL set: {'DATABASE_URL' in os.environ}")
print(f"  OPENAI_API_KEY set: {'OPENAI_API_KEY' in os.environ}")
print(f"  Using database: {'Supabase/Postgres' if settings.is_production else 'SQLite'}")
