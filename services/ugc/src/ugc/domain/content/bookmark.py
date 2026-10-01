"""Агрегат закладки фильма."""

from ugc.domain.content.user_action import UserAction


class Bookmark(UserAction):
    """Закладка, добавленная пользователем. Идемпотентна по паре."""
