"""Тесты структурированного JSON-логирования."""

import json
import logging
from typing import cast

from ugc.infrastructure.logging import RequestIdFilter, build_formatter


def _record(level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord(
        name="ugc.test",
        level=level,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )


def _format(service: str, include_http: bool = True) -> dict[str, object]:
    record = _record()
    RequestIdFilter(include_http).filter(record)
    return cast(
        dict[str, object],
        json.loads(build_formatter(service, include_http).format(record)),
    )


def test_formatter_emits_json_with_service() -> None:
    """Форматтер выдаёт JSON с именем сервиса и полями уровня."""
    parsed = _format("ugc-content")
    assert parsed["service"] == "ugc-content"
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello"


def test_http_formatter_includes_request_fields() -> None:
    """HTTP-форматтер содержит поля запроса со значениями по умолчанию."""
    parsed = _format("ugc-content")
    assert parsed["status"] == 0
    assert parsed["duration_ms"] == 0.0
    assert parsed["method"] == ""


def test_non_http_formatter_omits_request_fields() -> None:
    """Форматтер без HTTP-полей не выводит поля запроса."""
    parsed = _format("ugc-etl", include_http=False)
    assert "method" not in parsed
    assert "status" not in parsed
    assert parsed["service"] == "ugc-etl"


def test_extra_fields_override_defaults() -> None:
    """Дополнительные поля записи переопределяют значения по умолчанию."""
    record = _record()
    record.method = "GET"
    record.status = 200
    RequestIdFilter().filter(record)
    parsed = json.loads(build_formatter("ugc-content").format(record))
    assert parsed["method"] == "GET"
    assert parsed["status"] == 200
