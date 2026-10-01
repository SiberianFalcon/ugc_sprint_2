"""Value Object идентификатора фильма."""

from ugc.domain.content.exceptions import InvalidFilmIdError


class FilmId:
    """Идентификатор фильма, к которому относится контент."""

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise InvalidFilmIdError(
                "Идентификатор фильма не может быть пустым."
            )
        self._value = normalized

    @property
    def value(self) -> str:
        """Возвращает идентификатор фильма."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FilmId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
