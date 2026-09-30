"""Value Object адреса страницы."""

from urllib.parse import urlparse

from etl.domain.event.exceptions import InvalidPageUrlError


class PageUrl:
    """Адрес страницы, на которой произошло событие."""

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise InvalidPageUrlError("Адрес страницы не может быть пустым.")
        if not _is_valid_url(normalized):
            raise InvalidPageUrlError(
                "Адрес страницы должен быть абсолютным URL "
                "или абсолютным путём."
            )
        self._value = normalized

    @property
    def value(self) -> str:
        """Возвращает нормализованный адрес страницы."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PageUrl):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value


def _is_valid_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    return not parsed.scheme and value.startswith("/")
