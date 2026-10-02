"""Структурированное JSON-логирование и идентификатор запроса."""

import logging
import uuid
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter


_request_id: ContextVar[str] = ContextVar("request_id", default="-")

_HTTP_FIELD_DEFAULTS: dict[str, object] = {
    "method": "",
    "path": "",
    "status": 0,
    "duration_ms": 0.0,
}


def generate_request_id() -> str:
    """Генерирует идентификатор запроса."""
    return uuid.uuid4().hex


def set_request_id(value: str) -> None:
    """Задаёт идентификатор текущего запроса."""
    _request_id.set(value)


class RequestIdFilter(logging.Filter):
    """Подставляет идентификатор запроса и HTTP-поля по умолчанию."""

    def __init__(self, include_http: bool = True) -> None:
        super().__init__()
        self._defaults = _HTTP_FIELD_DEFAULTS if include_http else {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Дополняет запись лога идентификатором запроса."""
        record.request_id = _request_id.get()
        for field, default in self._defaults.items():
            if not hasattr(record, field):
                setattr(record, field, default)
        return True


def build_formatter(service: str, include_http: bool = True) -> JsonFormatter:
    """Создаёт JSON-форматтер с общими полями."""
    rename_fields = {
        "asctime": "ts",
        "levelname": "level",
        "name": "logger",
    }
    if include_http:
        fmt = (
            "%(asctime)s %(levelname)s %(name)s %(request_id)s "
            "%(method)s %(path)s %(status)s %(duration_ms)s %(message)s"
        )
    else:
        fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    return JsonFormatter(
        fmt,
        rename_fields=rename_fields,
        static_fields={"service": service},
    )


def configure_logging(service: str, include_http: bool = True) -> None:
    """Настраивает корневой логгер на JSON-вывод в stdout."""
    handler = logging.StreamHandler()
    handler.setFormatter(build_formatter(service, include_http))
    handler.addFilter(RequestIdFilter(include_http))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
