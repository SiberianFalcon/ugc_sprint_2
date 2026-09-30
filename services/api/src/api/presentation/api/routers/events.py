"""Маршруты приёма пользовательских событий."""

from fastapi import APIRouter, status

from api.application.dto.collect_event import CollectEventCommand
from api.presentation.api.dependencies import (
    EventServiceDependency,
    UserIdDependency,
)
from api.presentation.api.schemas import (
    EventAcceptedResponse,
    EventRequest,
)


router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def collect_event(
    event: EventRequest,
    user_id: UserIdDependency,
    service: EventServiceDependency,
) -> EventAcceptedResponse:
    """Принимает пользовательское событие и передаёт его в очередь."""
    collected = await service.collect_event(
        CollectEventCommand(
            user_id=str(user_id),
            event_type=event.event_type,
            event_id=event.event_id,
            event_time=event.event_time,
            payload=event.payload,
        )
    )
    return EventAcceptedResponse(event_id=str(collected.event_id))
