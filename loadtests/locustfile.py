"""Нагрузочные сценарии Locust для API пользовательского контента."""

import random

from locust import HttpUser, between, task


FILMS = [f"film-{index}" for index in range(1, 501)]
TEXT = "тестовая рецензия"


class ContentUser(HttpUser):
    """Эмулирует пользователя сервиса контента."""

    wait_time = between(0.1, 0.5)

    @task(4)
    def like_film(self) -> None:
        """Ставит лайк фильму."""
        film = random.choice(FILMS)
        self.client.put(f"/api/v1/likes/{film}")

    @task(3)
    def read_like_status(self) -> None:
        """Читает состояние лайка фильма."""
        film = random.choice(FILMS)
        self.client.get(f"/api/v1/likes/{film}")

    @task(2)
    def add_bookmark(self) -> None:
        """Добавляет фильм в закладки."""
        film = random.choice(FILMS)
        self.client.put(f"/api/v1/bookmarks/{film}")

    @task(2)
    def create_review(self) -> None:
        """Создаёт рецензию на фильм."""
        film = random.choice(FILMS)
        self.client.post(
            "/api/v1/reviews",
            json={
                "film_id": film,
                "rating": random.randint(1, 10),
                "text": TEXT,
            },
        )

    @task(1)
    def list_reviews(self) -> None:
        """Читает список рецензий фильма."""
        film = random.choice(FILMS)
        self.client.get("/api/v1/reviews", params={"film_id": film})
