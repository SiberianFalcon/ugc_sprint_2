"""Точка входа сервиса ugc."""

import asyncio

import uvicorn

from ugc.infrastructure.container import InfrastructureDependencyContainer
from ugc.infrastructure.settings import AppSettings
from ugc.presentation.api.application import build_application
from ugc.presentation.container import ApplicationDependencyContainer


async def assemble() -> tuple[AppSettings, ApplicationDependencyContainer]:
    """Собирает зависимости приложения."""
    settings = AppSettings.load()
    infrastructure = await InfrastructureDependencyContainer.assemble(settings)
    application = await ApplicationDependencyContainer.assemble(infrastructure)
    return settings, application


def main() -> None:
    """Запускает HTTP-сервер сервиса."""
    settings, container = asyncio.run(assemble())
    application = build_application(settings, container)
    uvicorn.run(
        application,
        host=settings.presentation.host,
        port=settings.presentation.port,
    )


if __name__ == "__main__":
    main()
