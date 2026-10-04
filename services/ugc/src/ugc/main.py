"""Точка входа сервиса ugc."""

import uvicorn

from ugc.infrastructure.container import InfrastructureDependencyContainer
from ugc.infrastructure.logging import configure_logging
from ugc.infrastructure.sentry import init_sentry
from ugc.infrastructure.settings import AppSettings
from ugc.presentation.api.application import build_application
from ugc.presentation.container import ApplicationDependencyContainer


async def assemble(
    settings: AppSettings,
) -> ApplicationDependencyContainer:
    """Собирает зависимости приложения, открывая соединение с MongoDB."""
    infrastructure = await InfrastructureDependencyContainer.assemble(settings)
    return await ApplicationDependencyContainer.assemble(infrastructure)


def main() -> None:
    """Запускает HTTP-сервер сервиса."""
    configure_logging("ugc-content")
    settings = AppSettings.load()
    init_sentry(settings.sentry)
    application = build_application(settings, lambda: assemble(settings))
    uvicorn.run(
        application,
        host=settings.presentation.host,
        port=settings.presentation.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
