"""Порт хранения закладок."""

from typing import Protocol

from ugc.application.ports.user_action_repository import (
    UserActionRepository,
)


class BookmarkRepository(UserActionRepository, Protocol):
    """Хранит закладки пользователей."""
