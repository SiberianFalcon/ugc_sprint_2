"""Тесты HTTP-эндпоинта приёма событий."""

from fastapi.testclient import TestClient

from api.application.events.services import EventApplicationService
from api.infrastructure.clock import SystemClock
from api.infrastructure.container import InfrastructureDependencyContainer
from api.infrastructure.kafka.event_producer import KafkaEventProducer
from api.infrastructure.security.token_verifier import JwtTokenVerifier
from api.infrastructure.settings import AppSettings
from api.presentation.api.application import build_application
from api.presentation.api.dependencies import get_event_service
from api.presentation.container import ApplicationDependencyContainer


class _FakeCollected:
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id


class _FakeEventService:
    async def collect_event(self, command: object) -> _FakeCollected:
        return _FakeCollected("event-1")


def _build_container(settings: AppSettings) -> ApplicationDependencyContainer:
    infrastructure = InfrastructureDependencyContainer(
        settings=settings,
        clock=SystemClock(),
        event_producer=KafkaEventProducer(settings.infrastructure.kafka),
        token_verifier=JwtTokenVerifier(settings.auth),
    )
    return ApplicationDependencyContainer(
        infrastructure=infrastructure,
        event_service=EventApplicationService(
            producer=infrastructure.event_producer,
            clock=infrastructure.clock,
        ),
    )


def _build_client() -> TestClient:
    settings = AppSettings.load()
    container = _build_container(settings)
    application = build_application(settings, container)
    application.dependency_overrides[get_event_service] = _FakeEventService
    return TestClient(application)


def _build_real_client() -> TestClient:
    settings = AppSettings.load()
    container = _build_container(settings)
    return TestClient(build_application(settings, container))


def test_collect_event_endpoint_returns_accepted() -> None:
    """Корректный запрос принимается и возвращает идентификатор события."""
    response = _build_client().post(
        "/events",
        json={
            "event_type": "click",
            "payload": {"page_url": "/movie", "element_id": "play"},
        },
    )
    assert response.status_code == 202
    assert response.json() == {"event_id": "event-1"}


def test_collect_event_endpoint_requires_event_type() -> None:
    """Запрос без event_type отклоняется с ошибкой валидации."""
    response = _build_client().post("/events", json={"payload": {}})
    assert response.status_code == 422


def test_collect_event_endpoint_rejects_malformed_page_url() -> None:
    """Неверный URL возвращает 400, а не 500."""
    response = _build_real_client().post(
        "/events",
        json={
            "event_type": "page_view",
            "payload": {"page_url": "http://["},
        },
    )
    assert response.status_code == 400
