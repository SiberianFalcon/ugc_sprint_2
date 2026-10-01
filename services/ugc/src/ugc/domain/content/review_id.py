"""Value Object идентификатора рецензии."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ugc.domain.content.exceptions import InvalidReviewIdError


@dataclass(frozen=True, slots=True)
class ReviewId:
    """Уникальный идентификатор рецензии."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidReviewIdError(
                "Идентификатор рецензии не может быть пустым."
            )

    @classmethod
    def new(cls) -> ReviewId:
        """Создаёт новый случайный идентификатор рецензии."""
        return cls(uuid.uuid4().hex)

    def __str__(self) -> str:
        return self.value
