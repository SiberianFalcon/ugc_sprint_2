"""Middleware идентификатора запроса и логирования доступа."""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from ugc.infrastructure.logging import generate_request_id, set_request_id


logger = logging.getLogger("ugc.access")


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Назначает идентификатор запроса и логирует завершение обработки."""
    request_id = request.headers.get("x-request-id") or generate_request_id()
    set_request_id(request_id)
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request handled",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response
