# Нагрузочное тестирование API контента

Сценарии Locust для проверки API лайков, закладок и рецензий и подтверждения
требования чтения **< 200 мс**.

## Сценарии

`ContentUser` выполняет операции с весами:

| Операция | Вес | Метод |
| --- | --- | --- |
| Поставить лайк | 4 | `PUT /api/v1/likes/{film_id}` |
| Состояние лайка | 3 | `GET /api/v1/likes/{film_id}` |
| Добавить закладку | 2 | `PUT /api/v1/bookmarks/{film_id}` |
| Создать рецензию | 2 | `POST /api/v1/reviews` |
| Список рецензий | 1 | `GET /api/v1/reviews?film_id=` |

Данные распределяются по пулу из 500 фильмов.

## Запуск

Сначала поднимите сервис контента и MongoDB:

```bash
sudo docker compose up -d --build ugc
```

Веб-интерфейс Locust (http://localhost:8089):

```bash
uv run locust -f loadtests/locustfile.py --host http://localhost:8001
```

Прогон без интерфейса с сохранением отчёта:

```bash
uv run locust -f loadtests/locustfile.py --host http://localhost:8001 \
  --headless -u 100 -r 10 -t 60s --csv loadtests/results/locust
```

Результаты (перцентили задержек по каждому эндпоинту) сохраняются в
`loadtests/results/locust_stats.csv` и отражаются в корневом `README.md`.
