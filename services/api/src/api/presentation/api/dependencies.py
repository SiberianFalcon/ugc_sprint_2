"""FastAPI-зависимости внедрения сервисов приложения."""

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.application.errors import InvalidTokenError
from api.application.events.services import EventApplicationService
from api.domain.event.user_id import UserId
from api.presentation.container import ApplicationDependencyContainer


_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> ApplicationDependencyContainer:
    """Возвращает контейнер зависимостей приложения."""
    return cast(ApplicationDependencyContainer, request.app.state.container)


ContainerDependency = Annotated[
    ApplicationDependencyContainer, Depends(get_container)
]


def get_event_service(
    container: ContainerDependency,
) -> EventApplicationService:
    """Возвращает прикладной сервис приёма событий."""
    return container.event_service


EventServiceDependency = Annotated[
    EventApplicationService, Depends(get_event_service)
]


async def get_user_id(
    container: ContainerDependency,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> UserId:
    """Определяет пользователя по токену; без токена — анонимный."""
    if credentials is None:
        return UserId.anonymous()
    try:
        return await container.infrastructure.token_verifier.verify(
            credentials.credentials
        )
    except InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error


UserIdDependency = Annotated[UserId, Depends(get_user_id)]
