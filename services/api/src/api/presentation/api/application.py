"""Фабрика FastAPI-приложения."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.infrastructure.settings import AppSettings
from api.presentation.api.errors import register_exception_handlers
from api.presentation.api.routers import events, health
from api.presentation.container import ApplicationDependencyContainer


def build_application(
    settings: AppSettings,
    container: ApplicationDependencyContainer,
) -> FastAPI:
    """Собирает FastAPI-приложение сервиса."""
    application = FastAPI(title="UGC Analytics API", lifespan=_lifespan)
    application.state.settings = settings
    application.state.container = container
    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(events.router)
    return application


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    container: ApplicationDependencyContainer = application.state.container
    await container.infrastructure.event_producer.start()
    try:
        yield
    finally:
        await container.infrastructure.event_producer.stop()
