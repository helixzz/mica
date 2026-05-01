"""Application configuration.

Loaded from environment variables. See deploy/.env.example for the full list.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "Mica"
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "1.3.1"
    debug: bool = False

    # ── API ──
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:5173",
        ]
    )
    cors_allow_all: bool = False

    # ── Database ──
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://mica:mica@localhost:5432/mica"  # type: ignore[arg-type]
    )
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # ── Security ──
    secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_minimum_32_chars_required_for_jwt_signing_skeleton"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours for dev convenience
    refresh_token_expire_days: int = 7

    # ── i18n ──
    default_locale: str = "zh-CN"
    supported_locales: list[str] = Field(default_factory=lambda: ["zh-CN", "en-US"])

    # ── Seed data ──
    seed_default_password: str = "MicaDev2026!"
    auto_seed_on_startup: bool = True

    media_root: str = "/app/media"
    download_token_ttl_seconds: int = 3600

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
