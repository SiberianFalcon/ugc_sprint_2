"""Настройки ETL-сервиса, загружаемые из переменных окружения."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaSettings(BaseSettings):
    """Параметры подключения к Kafka для чтения событий."""

    model_config = SettingsConfigDict(
        env_prefix="APP_KAFKA_", env_file=".env", extra="ignore"
    )

    bootstrap_servers: str = "localhost:9092"
    topic: str = "events"
    group_id: str = "ugc-etl"
    dlq_topic: str = "events.dlq"
    client_id: str = "ugc-etl"

    @field_validator(
        "bootstrap_servers", "topic", "group_id", "dlq_topic", "client_id"
    )
    @classmethod
    def _validate_not_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("значение не должно быть пустым")
        return value


class ClickHouseSettings(BaseSettings):
    """Параметры подключения к ClickHouse."""

    model_config = SettingsConfigDict(
        env_prefix="APP_CLICKHOUSE_", env_file=".env", extra="ignore"
    )

    host: str = "localhost"
    port: int = 8123
    database: str = "ugc"
    table: str = "events"
    username: str = "default"
    password: str = ""

    @field_validator("host", "database", "table", "username")
    @classmethod
    def _validate_not_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("значение не должно быть пустым")
        return value

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port должен быть в диапазоне от 1 до 65535")
        return value


class BatchSettings(BaseSettings):
    """Параметры формирования пакета событий."""

    model_config = SettingsConfigDict(
        env_prefix="APP_BATCH_", env_file=".env", extra="ignore"
    )

    max_size: int = 1000
    timeout_seconds: float = 5.0

    @field_validator("max_size")
    @classmethod
    def _validate_max_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_size должен быть положительным")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout_seconds должен быть положительным")
        return value


class MonitoringSettings(BaseSettings):
    """Параметры мониторинга ресурсов процесса."""

    model_config = SettingsConfigDict(
        env_prefix="APP_MONITORING_", env_file=".env", extra="ignore"
    )

    memory_threshold_mb: int = 512
    interval_seconds: float = 10.0

    @field_validator("memory_threshold_mb")
    @classmethod
    def _validate_threshold(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("memory_threshold_mb должен быть положительным")
        return value

    @field_validator("interval_seconds")
    @classmethod
    def _validate_interval(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("interval_seconds должен быть положительным")
        return value


class RetrySettings(BaseSettings):
    """Параметры повторных попыток при сбоях."""

    model_config = SettingsConfigDict(
        env_prefix="APP_RETRY_", env_file=".env", extra="ignore"
    )

    backoff_seconds: float = 5.0

    @field_validator("backoff_seconds")
    @classmethod
    def _validate_backoff(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("backoff_seconds должен быть положительным")
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
    clickhouse: ClickHouseSettings


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Полный набор настроек приложения."""

    infrastructure: InfrastructureSettings
    batch: BatchSettings
    monitoring: MonitoringSettings
    retry: RetrySettings
    sentry: SentrySettings

    @classmethod
    def load(cls) -> AppSettings:
        """Загружает настройки из переменных окружения."""
        return cls(
            infrastructure=InfrastructureSettings(
                kafka=KafkaSettings(),
                clickhouse=ClickHouseSettings(),
            ),
            batch=BatchSettings(),
            monitoring=MonitoringSettings(),
            retry=RetrySettings(),
            sentry=SentrySettings(),
        )
