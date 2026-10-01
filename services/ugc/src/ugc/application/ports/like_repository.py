"""Порт хранения лайков."""

from typing import Protocol

from ugc.application.ports.user_action_repository import (
    UserActionRepository,
)


class LikeRepository(UserActionRepository, Protocol):
    """Хранит лайки пользователей."""
