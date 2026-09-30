"""Тесты аутентификации API."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from api.application.dto.collect_event import CollectEventCommand
from api.application.events.services import EventApplicationService
from api.domain.event.user_id import UserId
from api.infrastructure.clock import SystemClock
from api.infrastructure.container import InfrastructureDependencyContainer
from api.infrastructure.kafka.event_producer import KafkaEventProducer
from api.infrastructure.security.token_verifier import JwtTokenVerifier
from api.infrastructure.settings import AppSettings
from api.presentation.api.application import build_application
from api.presentation.api.dependencies import get_event_service, get_user_id
from api.presentation.container import ApplicationDependencyContainer


class _Captured:
    def __init__(self) -> None:
        self.event_id = "event-1"


def _container() -> ApplicationDependencyContainer:
    settings = AppSettings.load()
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


async def test_get_user_id_anonymous_without_token() -> None:
    """Без токена пользователь считается анонимным."""
    result = await get_user_id(_container(), None)
    assert result.is_anonymous


async def test_get_user_id_raises_401_on_invalid_token() -> None:
    """Невалидный токен приводит к 401."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="bad"
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_user_id(_container(), credentials)
    assert exc_info.value.status_code == 401


async def test_get_user_id_returns_from_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Валидный токен даёт идентификатор из верификатора."""
    container = _container()

    async def _verify(token: str) -> UserId:
        return UserId("user-1")

    monkeypatch.setattr(
        container.infrastructure.token_verifier, "verify", _verify
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="good"
    )
    result = await get_user_id(container, credentials)
    assert result == UserId("user-1")


def test_event_endpoint_uses_anonymous_without_token() -> None:
    """Без токена событие записывается от анонимного пользователя."""
    settings = AppSettings.load()
    container = _container()
    app = build_application(settings, container)
    captured: dict[str, str] = {}

    class _Svc:
        async def collect_event(
            self, command: CollectEventCommand
        ) -> _Captured:
            captured["user_id"] = command.user_id
            return _Captured()

    app.dependency_overrides[get_event_service] = _Svc
    client = TestClient(app)
    response = client.post(
        "/events",
        json={"event_type": "page_view", "payload": {"page_url": "/movie"}},
    )

    assert response.status_code == 202
    assert captured["user_id"] == "anonymous"
