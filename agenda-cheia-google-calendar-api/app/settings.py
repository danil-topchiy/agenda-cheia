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
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_client_secrets_file: str | None = None
    google_oauth_redirect_uri: str = "http://127.0.0.1:8001/auth/google/callback"
    google_oauth_scopes: str = (
        "openid https://www.googleapis.com/auth/userinfo.email "
        "https://www.googleapis.com/auth/calendar.events"
    )
    google_oauth_prompt_consent: bool = True

    default_timezone: str = "America/Sao_Paulo"
    database_url: str = "sqlite:///./calendar_sync.db"

    google_webhook_base_url: str | None = None
    google_webhook_token: str | None = None
    watch_ttl_seconds: int = Field(default=604800, ge=60)
    cors_allowed_origins: str = "*"

    enable_polling_on_startup: bool = False
    poll_interval_seconds: int = Field(default=300, ge=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
