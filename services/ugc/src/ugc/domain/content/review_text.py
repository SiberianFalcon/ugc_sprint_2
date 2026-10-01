"""Value Object текста рецензии."""

from ugc.domain.content.exceptions import InvalidReviewTextError


class ReviewText:
    """Текст рецензии пользователя."""

    MAX_LENGTH = 5000

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise InvalidReviewTextError(
                "Текст рецензии не может быть пустым."
            )
        if len(normalized) > self.MAX_LENGTH:
            raise InvalidReviewTextError(
                f"Текст рецензии длиннее {self.MAX_LENGTH} символов."
            )
        self._value = normalized

    @property
    def value(self) -> str:
        """Возвращает текст рецензии."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReviewText):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
