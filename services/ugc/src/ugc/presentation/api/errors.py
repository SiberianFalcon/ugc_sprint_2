"""Обработчики ошибок API-слоя."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ugc.application.errors import (
    ReviewAccessDeniedError,
    ReviewConflictError,
    ReviewNotFoundError,
)
from ugc.domain.content.exceptions import ContentError


def register_exception_handlers(application: FastAPI) -> None:
    """Регистрирует обработчики ошибок приложения."""
    application.add_exception_handler(ContentError, _domain_error_handler)
    application.add_exception_handler(ReviewNotFoundError, _not_found_handler)
    application.add_exception_handler(
        ReviewAccessDeniedError, _forbidden_handler
    )
    application.add_exception_handler(ReviewConflictError, _conflict_handler)


async def _domain_error_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Преобразует доменную ошибку в ответ 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(error)},
    )


async def _not_found_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Преобразует отсутствие рецензии в ответ 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(error)},
    )


async def _forbidden_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Преобразует отсутствие доступа в ответ 403."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(error)},
    )


async def _conflict_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Преобразует конфликт версий в ответ 409."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(error)},
    )
