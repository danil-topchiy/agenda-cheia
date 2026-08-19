from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    pix_api_base_url: str = Field(
        default="http://127.0.0.1:8000", alias="PIX_API_BASE_URL"
    )
    public_base_url: str = Field(
        default="http://127.0.0.1:8010", alias="PUBLIC_BASE_URL"
    )
    forward_webhook_to_pix_api: bool = Field(
        default=True, alias="FORWARD_WEBHOOK_TO_PIX_API"
    )
    request_timeout: float = Field(default=20.0, alias="REQUEST_TIMEOUT")
    webhook_event_limit: int = Field(default=200, alias="WEBHOOK_EVENT_LIMIT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("pix_api_base_url", "public_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url}/webhooks/woovi"


@lru_cache
def get_settings() -> Settings:
    return Settings()

