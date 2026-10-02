"""Инициализация Sentry SDK для HTTP-сервиса."""

from __future__ import annotations

import logging

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.types import Event, Hint

from ugc.infrastructure.settings import SentrySettings


def init_sentry(settings: SentrySettings) -> None:
    """Подключает Sentry, если задан DSN и включена инициализация."""
    if not settings.enabled or not settings.dsn:
        return
    sentry_sdk.init(
        dsn=settings.dsn,
        environment=settings.environment,
        traces_sample_rate=settings.traces_sample_rate,
        send_default_pii=False,
        before_send=scrub_event,
        integrations=[
            AsyncioIntegration(),
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.WARNING, event_level=logging.ERROR
            ),
        ],
    )


def scrub_event(event: Event, hint: Hint) -> Event | None:
    """Удаляет чувствительные заголовки из события."""
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            headers.pop("Authorization", None)
            headers.pop("authorization", None)
    return event
