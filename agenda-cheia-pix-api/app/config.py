from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    woovi_app_id: str | None = Field(default=None, alias="WOOVI_APP_ID")
    woovi_api_base_url: str = Field(
        default="https://api.woovi.com", alias="WOOVI_API_BASE_URL"
    )
    database_path: str = Field(default="data/agenda_cheia_pix.db", alias="DATABASE_PATH")
    woovi_webhook_authorization: str | None = Field(
        default=None, alias="WOOVI_WEBHOOK_AUTHORIZATION"
    )
    woovi_webhook_verify_signature: bool = Field(
        default=True, alias="WOOVI_WEBHOOK_VERIFY_SIGNATURE"
    )
    woovi_webhook_public_keys_url: str | None = Field(
        default=None, alias="WOOVI_WEBHOOK_PUBLIC_KEYS_URL"
    )
    woovi_request_timeout: float = Field(default=15.0, alias="WOOVI_REQUEST_TIMEOUT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator(
        "woovi_app_id",
        "woovi_webhook_authorization",
        "woovi_webhook_public_keys_url",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("woovi_api_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def charge_url(self) -> str:
        return f"{self.woovi_api_base_url}/api/v1/charge"

    @property
    def webhook_public_keys_url(self) -> str:
        if self.woovi_webhook_public_keys_url:
            return self.woovi_webhook_public_keys_url
        return f"{self.woovi_api_base_url}/api/v1/webhook/public-keys"


@lru_cache
def get_settings() -> Settings:
    return Settings()
