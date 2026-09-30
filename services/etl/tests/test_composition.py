"""Тест сборки зависимостей ETL-сервиса."""

from etl.application.transfer.services import EventTransferService
from etl.composition import ApplicationDependencyContainer
from etl.infrastructure.container import InfrastructureDependencyContainer
from etl.infrastructure.settings import AppSettings


async def test_composition_builds_transfer_service() -> None:
    """Сборка создаёт сервис переноса без подключения к внешним системам."""
    settings = AppSettings.load()
    infrastructure = await InfrastructureDependencyContainer.assemble(settings)

    application = await ApplicationDependencyContainer.assemble(infrastructure)

    assert isinstance(application.transfer_service, EventTransferService)
