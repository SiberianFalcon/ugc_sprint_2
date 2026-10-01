"""Агрегат лайка фильма."""

from ugc.domain.content.user_action import UserAction


class Like(UserAction):
    """Лайк, поставленный пользователем фильму. Идемпотентен по паре."""
