"""Тесты health-эндпоинтов API."""

import pytest
from fastapi.testclient import TestClient

from api.application.events.services import EventApplicationService
from api.infrastructure.clock import SystemClock
from api.infrastructure.container import InfrastructureDependencyContainer
from api.infrastructure.kafka.event_producer import KafkaEventProducer
from api.infrastructure.security.token_verifier import JwtTokenVerifier
from api.infrastructure.settings import AppSettings
from api.presentation.api.application import build_application
from api.presentation.container import ApplicationDependencyContainer


def _client(producer: KafkaEventProducer) -> TestClient:
    settings = AppSettings.load()
    infrastructure = InfrastructureDependencyContainer(
        settings=settings,
        clock=SystemClock(),
        event_producer=producer,
        token_verifier=JwtTokenVerifier(settings.auth),
    )
    container = ApplicationDependencyContainer(
        infrastructure=infrastructure,
        event_service=EventApplicationService(
            producer=producer,
            clock=infrastructure.clock,
        ),
    )
    return TestClient(build_application(settings, container))


def _producer() -> KafkaEventProducer:
    return KafkaEventProducer(AppSettings.load().infrastructure.kafka)


def test_health_live_ok() -> None:
    """Проверка живости всегда отвечает 200."""
    response = _client(_producer()).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_503_when_kafka_unavailable() -> None:
    """При недоступной Kafka готовность отвечает 503."""
    response = _client(_producer()).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["kafka"] == "down"


def test_health_ready_ok_when_kafka_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """При доступной Kafka готовность отвечает 200."""
    producer = _producer()

    async def _ok() -> bool:
        return True

    monkeypatch.setattr(producer, "check", _ok)
    response = _client(producer).get("/health/ready")
    assert response.status_code == 200
    assert response.json()["dependencies"]["kafka"] == "ok"
