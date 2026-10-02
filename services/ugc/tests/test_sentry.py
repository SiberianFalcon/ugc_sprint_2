"""Тесты интеграции с Sentry."""

from typing import Any, cast

from sentry_sdk.types import Event

from ugc.infrastructure.sentry import scrub_event


def test_scrub_event_removes_authorization_header() -> None:
    """Заголовок Authorization удаляется из события."""
    event = cast(
        Event,
        {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret",
                    "Content-Type": "application/json",
                }
            }
        },
    )
    result = cast(dict[str, Any], scrub_event(event, {}))
    headers = result["request"]["headers"]
    assert "Authorization" not in headers
    assert headers["Content-Type"] == "application/json"


def test_scrub_event_handles_missing_request() -> None:
    """Событие без блока request возвращается без изменений."""
    event = cast(Event, {"message": "boom"})
    result = cast(dict[str, Any], scrub_event(event, {}))
    assert result == {"message": "boom"}
