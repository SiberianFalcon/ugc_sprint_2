"""FastAPI-зависимости внедрения сервисов приложения."""

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ugc.application.content.services import (
    BookmarkApplicationService,
    LikeApplicationService,
    ReviewApplicationService,
)
from ugc.application.errors import InvalidTokenError
from ugc.domain.content.user_id import UserId
from ugc.presentation.container import ApplicationDependencyContainer


_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> ApplicationDependencyContainer:
    """Возвращает контейнер зависимостей приложения."""
    return cast(ApplicationDependencyContainer, request.app.state.container)


ContainerDependency = Annotated[
    ApplicationDependencyContainer, Depends(get_container)
]


def get_like_service(
    container: ContainerDependency,
) -> LikeApplicationService:
    """Возвращает сервис лайков."""
    return container.like_service


def get_bookmark_service(
    container: ContainerDependency,
) -> BookmarkApplicationService:
    """Возвращает сервис закладок."""
    return container.bookmark_service


def get_review_service(
    container: ContainerDependency,
) -> ReviewApplicationService:
    """Возвращает сервис рецензий."""
    return container.review_service


LikeServiceDependency = Annotated[
    LikeApplicationService, Depends(get_like_service)
]
BookmarkServiceDependency = Annotated[
    BookmarkApplicationService, Depends(get_bookmark_service)
]
ReviewServiceDependency = Annotated[
    ReviewApplicationService, Depends(get_review_service)
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
