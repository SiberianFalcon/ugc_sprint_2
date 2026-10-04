"""Настройки сервиса ugc, загружаемые из переменных окружения."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSettings(BaseSettings):
    """Параметры подключения к MongoDB."""

    model_config = SettingsConfigDict(
        env_prefix="APP_MONGO_", env_file=".env", extra="ignore"
    )

    uri: str = "mongodb://localhost:27017"
    database: str = "ugc"
    like_collection: str = "likes"
    bookmark_collection: str = "bookmarks"
    review_collection: str = "reviews"

    @field_validator(
        "uri",
        "database",
        "like_collection",
        "bookmark_collection",
        "review_collection",
    )
    @classmethod
    def _validate_not_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("значение не должно быть пустым")
        return value


class PresentationSettings(BaseSettings):
    """Параметры HTTP-сервера."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    host: str = "0.0.0.0"
    port: int = 8001

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port должен быть в диапазоне от 1 до 65535")
        return value


class AuthSettings(BaseSettings):
    """Параметры проверки токенов доступа."""

    model_config = SettingsConfigDict(
        env_prefix="APP_AUTH_", env_file=".env", extra="ignore"
    )

    jwks_url: str = ""
    issuer: str = "auth-service"
    timeout_seconds: float = 5.0
    jwks_cache_ttl_seconds: float = 300.0
    jwks_refresh_min_seconds: float = 30.0

    @field_validator(
        "timeout_seconds",
        "jwks_cache_ttl_seconds",
        "jwks_refresh_min_seconds",
    )
    @classmethod
    def _validate_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("значение должно быть положительным")
        return value


class SentrySettings(BaseSettings):
    """Параметры подключения к Sentry."""

    model_config = SettingsConfigDict(
        env_prefix="APP_SENTRY_", env_file=".env", extra="ignore"
    )

    dsn: str = ""
    enabled: bool = False
    environment: str = "development"
    traces_sample_rate: float = 0.0

    @field_validator("traces_sample_rate")
    @classmethod
    def _validate_sample_rate(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                "traces_sample_rate должен быть в диапазоне от 0 до 1"
            )
        return value


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Полный набор настроек приложения."""

    mongo: MongoSettings
    presentation: PresentationSettings
    auth: AuthSettings
    sentry: SentrySettings

    @classmethod
    def load(cls) -> AppSettings:
        """Загружает настройки из переменных окружения."""
        return cls(
            mongo=MongoSettings(),
            presentation=PresentationSettings(),
            auth=AuthSettings(),
            sentry=SentrySettings(),
        )
