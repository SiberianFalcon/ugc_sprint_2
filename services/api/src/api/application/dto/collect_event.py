"""Команда приёма пользовательского события."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CollectEventCommand:
    """Входные данные сценария приёма события."""

    user_id: str
    event_type: str
    event_id: str | None = None
    event_time: str | None = None
    payload: Mapping[str, object] = field(default_factory=dict)
