"""Маршруты проверки работоспособности сервиса."""

from typing import Any

from fastapi import APIRouter, Response, status

from ugc.presentation.api.dependencies import ContainerDependency


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    """Сообщает, что процесс сервиса запущен."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    container: ContainerDependency, response: Response
) -> dict[str, Any]:
    """Сообщает о готовности сервиса и доступности MongoDB."""
    mongo_ready = await container.infrastructure.connection.check()
    if not mongo_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if mongo_ready else "degraded",
        "dependencies": {"mongodb": "ok" if mongo_ready else "down"},
    }
