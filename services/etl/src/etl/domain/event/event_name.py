"""Value Object имени кастомного события."""

from etl.domain.event.exceptions import InvalidEventNameError


class EventName:
    """Имя кастомного события."""

    MAX_LENGTH = 100

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise InvalidEventNameError("Имя события не может быть пустым.")
        if len(normalized) > self.MAX_LENGTH:
            raise InvalidEventNameError(
                f"Имя события длиннее {self.MAX_LENGTH} символов."
            )
        self._value = normalized

    @property
    def value(self) -> str:
        """Возвращает имя события."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventName):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
