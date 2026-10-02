"""Точка входа ETL-сервиса."""

import asyncio
import signal

from etl.application.transfer.services import EventTransferService
from etl.composition import ApplicationDependencyContainer
from etl.infrastructure.container import InfrastructureDependencyContainer
from etl.infrastructure.logging import configure_logging
from etl.infrastructure.sentry import init_sentry
from etl.infrastructure.settings import AppSettings


async def run() -> None:
    """Запускает фоновый цикл переноса событий."""
    settings = AppSettings.load()
    init_sentry(settings.sentry)
    infrastructure = await InfrastructureDependencyContainer.assemble(settings)
    application = await ApplicationDependencyContainer.assemble(infrastructure)
    service = application.transfer_service
    monitor = infrastructure.memory_monitor

    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(stop_signal, _schedule_stop, loop, service)

    monitor_task = asyncio.create_task(monitor.run())
    try:
        await service.run()
    finally:
        await service.stop()
        await monitor.stop()
        await monitor_task


def _schedule_stop(
    loop: asyncio.AbstractEventLoop, service: EventTransferService
) -> None:
    loop.create_task(service.stop())


def main() -> None:
    """Запускает ETL-сервис."""
    configure_logging("ugc-etl", include_http=False)
    asyncio.run(run())


if __name__ == "__main__":
    main()
