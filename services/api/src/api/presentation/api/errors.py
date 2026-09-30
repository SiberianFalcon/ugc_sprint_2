"""Обработчики ошибок API-слоя."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from api.domain.exceptions import DomainError


def register_exception_handlers(application: FastAPI) -> None:
    """Регистрирует обработчики ошибок приложения."""
    application.add_exception_handler(DomainError, _domain_error_handler)


async def _domain_error_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Преобразует доменную ошибку в ответ 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(error)},
    )
