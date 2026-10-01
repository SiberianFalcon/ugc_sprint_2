"""Value Object момента создания записи."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ugc.domain.content.exceptions import InvalidCreatedAtError


@dataclass(frozen=True, slots=True)
class CreatedAt:
    """Момент создания или изменения пользовательского контента."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            raise InvalidCreatedAtError(
                "Момент времени должен содержать часовой пояс."
            )

    def __str__(self) -> str:
        return self.value.isoformat()
