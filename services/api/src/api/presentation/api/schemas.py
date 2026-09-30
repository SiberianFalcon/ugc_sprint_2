"""Pydantic-модели запросов и ответов API-слоя."""

from typing import Any

from pydantic import BaseModel, Field


class EventRequest(BaseModel):
    """Запрос на приём пользовательского события."""

    event_type: str = Field(min_length=1)
    event_id: str | None = None
    event_time: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventAcceptedResponse(BaseModel):
    """Ответ на успешный приём события."""

    event_id: str
