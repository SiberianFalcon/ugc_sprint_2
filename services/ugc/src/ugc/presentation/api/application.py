"""Фабрика FastAPI-приложения."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ugc.infrastructure.settings import AppSettings
from ugc.presentation.api.errors import register_exception_handlers
from ugc.presentation.api.middleware import request_id_middleware
from ugc.presentation.api.routers import bookmarks, health, likes, reviews
from ugc.presentation.container import ApplicationDependencyContainer


def build_application(
    settings: AppSettings,
    container: ApplicationDependencyContainer,
) -> FastAPI:
    """Собирает FastAPI-приложение сервиса."""
    application = FastAPI(title="UGC Content API", lifespan=_lifespan)
    application.state.settings = settings
    application.state.container = container
    application.middleware("http")(request_id_middleware)
    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(likes.router)
    application.include_router(bookmarks.router)
    application.include_router(reviews.router)
    return application


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    container: ApplicationDependencyContainer = application.state.container
    try:
        yield
    finally:
        await container.infrastructure.connection.stop()
