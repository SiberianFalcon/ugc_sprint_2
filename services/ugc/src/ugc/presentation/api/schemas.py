"""Pydantic-модели запросов и ответов API-слоя."""

from pydantic import BaseModel, Field


REVIEW_TEXT_MAX_LENGTH = 5000


class ReviewCreateRequest(BaseModel):
    """Запрос на создание рецензии."""

    film_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=10)
    text: str = Field(min_length=1, max_length=REVIEW_TEXT_MAX_LENGTH)


class ReviewUpdateRequest(BaseModel):
    """Запрос на изменение рецензии."""

    rating: int = Field(ge=1, le=10)
    text: str = Field(min_length=1, max_length=REVIEW_TEXT_MAX_LENGTH)


class ReviewResponse(BaseModel):
    """Представление рецензии."""

    review_id: str
    user_id: str
    film_id: str
    rating: int
    text: str
    created_at: str
    updated_at: str


class ReviewListResponse(BaseModel):
    """Страница списка рецензий."""

    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int


class LikeStatusResponse(BaseModel):
    """Состояние лайка фильма."""

    film_id: str
    count: int
    liked_by_me: bool


class BookmarkStatusResponse(BaseModel):
    """Состояние закладки фильма."""

    film_id: str
    count: int
    bookmarked_by_me: bool


class FilmIdListResponse(BaseModel):
    """Список идентификаторов фильмов."""

    items: list[str]
