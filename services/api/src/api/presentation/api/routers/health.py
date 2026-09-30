"""Маршруты проверки работоспособности сервиса."""

from typing import Any

from fastapi import APIRouter, Response, status

from api.presentation.api.dependencies import ContainerDependency


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    """Сообщает, что процесс сервиса запущен."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    container: ContainerDependency, response: Response
) -> dict[str, Any]:
    """Сообщает о готовности сервиса и доступности зависимостей."""
    kafka_ready = await container.infrastructure.event_producer.check()
    if not kafka_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if kafka_ready else "degraded",
        "dependencies": {"kafka": "ok" if kafka_ready else "down"},
    }
