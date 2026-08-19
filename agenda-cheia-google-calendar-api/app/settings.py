from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Agenda Cheia Google Calendar API"
    google_calendar_id: str = "primary"
    google_credentials_file: str | None = None
    google_delegated_subject: str | None = None

    default_timezone: str = "America/Sao_Paulo"
    database_url: str = "sqlite:///./calendar_sync.db"

    google_webhook_base_url: str | None = None
    google_webhook_token: str | None = None
    watch_ttl_seconds: int = Field(default=604800, ge=60)

    enable_polling_on_startup: bool = False
    poll_interval_seconds: int = Field(default=300, ge=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
