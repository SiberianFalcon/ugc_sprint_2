"""Pydantic-модели запросов и ответов API-слоя."""

from pydantic import BaseModel, Field, field_validator

from ugc.domain.content.rating import Rating
from ugc.domain.content.review_text import ReviewText


class ReviewWriteRequest(BaseModel):
    """Общая часть запроса на запись рецензии."""

    rating: int = Field(ge=Rating.MIN_VALUE, le=Rating.MAX_VALUE)
    text: str

    @field_validator("text")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Текст рецензии не может быть пустым.")
        if len(normalized) > ReviewText.MAX_LENGTH:
            raise ValueError(
                f"Текст рецензии длиннее {ReviewText.MAX_LENGTH} символов."
            )
        return normalized


class ReviewCreateRequest(ReviewWriteRequest):
    """Запрос на создание рецензии."""

    film_id: str = Field(min_length=1)


class ReviewUpdateRequest(ReviewWriteRequest):
    """Запрос на изменение рецензии."""


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
    """Страница списка идентификаторов фильмов."""

    items: list[str]
    total: int
    page: int
    page_size: int
