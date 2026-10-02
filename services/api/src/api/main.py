"""Точка входа API-сервиса."""

import asyncio

import uvicorn

from api.infrastructure.container import InfrastructureDependencyContainer
from api.infrastructure.logging import configure_logging
from api.infrastructure.sentry import init_sentry
from api.infrastructure.settings import AppSettings
from api.presentation.api.application import build_application
from api.presentation.container import ApplicationDependencyContainer


async def assemble() -> tuple[AppSettings, ApplicationDependencyContainer]:
    """Собирает зависимости приложения."""
    settings = AppSettings.load()
    infrastructure = await InfrastructureDependencyContainer.assemble(settings)
    application = await ApplicationDependencyContainer.assemble(infrastructure)
    return settings, application


def main() -> None:
    """Запускает HTTP-сервер сервиса."""
    configure_logging("ugc-api")
    settings, container = asyncio.run(assemble())
    init_sentry(settings.sentry)
    application = build_application(settings, container)
    uvicorn.run(
        application,
        host=settings.presentation.host,
        port=settings.presentation.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
