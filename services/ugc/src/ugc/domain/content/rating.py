"""Value Object оценки рецензии."""

from __future__ import annotations

from dataclasses import dataclass

from ugc.domain.content.exceptions import InvalidRatingError


@dataclass(frozen=True, slots=True)
class Rating:
    """Оценка фильма в рецензии от 1 до 10."""

    MIN_VALUE = 1
    MAX_VALUE = 10

    value: int

    def __post_init__(self) -> None:
        if not self.MIN_VALUE <= self.value <= self.MAX_VALUE:
            raise InvalidRatingError(
                f"Оценка должна быть в диапазоне от "
                f"{self.MIN_VALUE} до {self.MAX_VALUE}."
            )

    def __str__(self) -> str:
        return str(self.value)
