"""Тесты настроек сервиса ugc."""

import pytest
from pydantic import ValidationError

from ugc.infrastructure.settings import (
    AuthSettings,
    MongoSettings,
    PresentationSettings,
)


def test_mongo_settings_reject_empty_uri() -> None:
    """Пустой адрес MongoDB отклоняется."""
    with pytest.raises(ValidationError):
        MongoSettings(uri="")


def test_mongo_settings_reject_empty_database() -> None:
    """Пустое имя базы данных отклоняется."""
    with pytest.raises(ValidationError):
        MongoSettings(database="")


def test_presentation_settings_reject_bad_port() -> None:
    """Порт вне диапазона отклоняется."""
    with pytest.raises(ValidationError):
        PresentationSettings(port=70000)


def test_auth_settings_reject_non_positive_timeout() -> None:
    """Неположительный таймаут отклоняется."""
    with pytest.raises(ValidationError):
        AuthSettings(timeout_seconds=0)
