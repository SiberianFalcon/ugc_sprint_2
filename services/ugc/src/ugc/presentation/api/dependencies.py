"""FastAPI-зависимости внедрения сервисов приложения."""

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Query, Request, status
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


@dataclass(frozen=True, slots=True)
class PageParams:
    """Параметры постраничной выдачи."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        """Возвращает смещение для запроса к хранилищу."""
        return (self.page - 1) * self.page_size


def get_page_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PageParams:
    """Возвращает параметры страницы из запроса."""
    return PageParams(page=page, page_size=page_size)


PageParamsDependency = Annotated[PageParams, Depends(get_page_params)]


async def get_required_user_id(
    container: ContainerDependency,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> UserId:
    """Требует подтверждённого пользователя; без токена — 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация.",
        )
    return await _verify_token(container, credentials.credentials)


async def get_optional_user_id(
    container: ContainerDependency,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> UserId | None:
    """Возвращает пользователя по токену или None без токена."""
    if credentials is None:
        return None
    return await _verify_token(container, credentials.credentials)


async def _verify_token(
    container: ApplicationDependencyContainer, token: str
) -> UserId:
    try:
        return await container.infrastructure.token_verifier.verify(token)
    except InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
        ) from error


RequiredUserIdDependency = Annotated[UserId, Depends(get_required_user_id)]
OptionalUserIdDependency = Annotated[
    UserId | None, Depends(get_optional_user_id)
]
