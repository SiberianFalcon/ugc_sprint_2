"""Value Object идентификатора элемента страницы."""

from etl.domain.event.exceptions import InvalidElementIdError


class ElementId:
    """Идентификатор элемента страницы, на котором произошёл клик."""

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise InvalidElementIdError(
                "Идентификатор элемента не может быть пустым."
            )
        self._value = normalized

    @property
    def value(self) -> str:
        """Возвращает идентификатор элемента."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ElementId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
