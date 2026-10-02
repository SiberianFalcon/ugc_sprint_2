"""Настройки API-сервиса, загружаемые из переменных окружения."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaSettings(BaseSettings):
    """Параметры подключения к Kafka и публикации событий."""

    model_config = SettingsConfigDict(
        env_prefix="APP_KAFKA_", env_file=".env", extra="ignore"
    )

    bootstrap_servers: str = "localhost:9092"
    topic: str = "events"
    client_id: str = "ugc-api"

    @field_validator("bootstrap_servers", "topic", "client_id")
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
    port: int = 8000

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port должен быть в диапазоне от 1 до 65535")
        return value


class ObservabilitySettings(BaseSettings):
    """Параметры трассировки и наблюдаемости."""

    model_config = SettingsConfigDict(
        env_prefix="APP_OTEL_", env_file=".env", extra="ignore"
    )

    enabled: bool = False
    service_name: str = "ugc-api"
    exporter_endpoint: str = "http://localhost:4318/v1/traces"
    sample_ratio: float = 1.0

    @field_validator("sample_ratio")
    @classmethod
    def _validate_sample_ratio(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("sample_ratio должен быть в диапазоне от 0 до 1")
        return value


class AuthSettings(BaseSettings):
    """Параметры проверки токенов доступа."""

    model_config = SettingsConfigDict(
        env_prefix="APP_AUTH_", env_file=".env", extra="ignore"
    )

    jwks_url: str = ""
    issuer: str = "auth-service"
    timeout_seconds: float = 5.0

    @field_validator("timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout_seconds должен быть положительным")
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
class InfrastructureSettings:
    """Группа инфраструктурных настроек."""

    kafka: KafkaSettings


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Полный набор настроек приложения."""

    infrastructure: InfrastructureSettings
    presentation: PresentationSettings
    observability: ObservabilitySettings
    auth: AuthSettings
    sentry: SentrySettings

    @classmethod
    def load(cls) -> AppSettings:
        """Загружает настройки из переменных окружения."""
        return cls(
            infrastructure=InfrastructureSettings(kafka=KafkaSettings()),
            presentation=PresentationSettings(),
            observability=ObservabilitySettings(),
            auth=AuthSettings(),
            sentry=SentrySettings(),
        )
