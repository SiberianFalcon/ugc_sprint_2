"""Ошибки агрегата события."""

from etl.domain.exceptions import DomainError


class EventError(DomainError):
    """Базовая ошибка агрегата события."""


class InvalidEventIdError(EventError):
    """Идентификатор события не соответствует требованиям."""


class InvalidUserIdError(EventError):
    """Идентификатор пользователя не соответствует требованиям."""


class InvalidEventTypeError(EventError):
    """Тип события не соответствует требованиям."""


class InvalidEventTimeError(EventError):
    """Время события не соответствует требованиям."""


class InvalidPayloadError(EventError):
    """Данные события не соответствуют требованиям."""


class InvalidPageUrlError(EventError):
    """Адрес страницы не соответствует требованиям."""


class InvalidElementIdError(EventError):
    """Идентификатор элемента не соответствует требованиям."""


class InvalidEventNameError(EventError):
    """Имя события не соответствует требованиям."""


class InvalidEventError(EventError):
    """Событие имеет недопустимое состояние."""
