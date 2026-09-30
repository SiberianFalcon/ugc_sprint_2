# Исследование выбора хранилища пользовательского контента

Сравнение MongoDB и PostgreSQL для хранения лайков, закладок и рецензий.
Цель — подтвердить выбор хранилища под требование чтения **< 200 мс** на
датасете **10+ млн записей**.

## Модель данных

Обе базы получают одинаковый набор записей:

| Поле | Тип | Комментарий |
| --- | --- | --- |
| `user_id` | text | уникален для записи |
| `film_id` | text | 50 000 фильмов |
| `kind` | text | `like` (60%), `bookmark` (30%), `review` (10%) |
| `rating` | int | оценка рецензии (1–10) |
| `review_text` | text | текст рецензии |
| `created_at` | timestamp | момент создания |

Индексы:

- уникальный `(user_id, film_id, kind)` — идемпотентность действий;
- `(film_id, kind, created_at DESC)` — постраничные списки и подсчёты.

## Запуск

Требуются Docker и `uv`. Скрипт сам поднимет контейнеры, наполнит базы и
проведёт замеры:

```bash
bash research/storage/run.sh
```

Число записей можно переопределить: `RECORDS=10000000 bash research/storage/run.sh`.

Отдельные шаги:

```bash
sudo docker compose -f research/storage/docker-compose.research.yml up -d
uv run --with 'psycopg[binary]' python research/storage/seed.py --records 10000000
uv run --with 'psycopg[binary]' python research/storage/benchmark.py
sudo docker compose -f research/storage/docker-compose.research.yml down -v
```

## Методика замеров

После прогрева (`--warmup`, по умолчанию 200 операций) измеряется по
1000 операций каждого типа; фиксируются p50, p95, p99 и среднее время:

- `read_point` — точечное чтение по `(user_id, film_id, kind)`;
- `read_count` — подсчёт лайков фильма;
- `read_list` — первые 20 рецензий фильма по убыванию даты;
- `write_upsert` — вставка/обновление действия;
- `delete` — удаление действия.

Контейнеры ограничены 2 ГБ памяти: MongoDB — кэш WiredTiger 1 ГБ,
PostgreSQL — `shared_buffers=1GB`.

## Результаты

Перцентили задержек в миллисекундах (заполняется после прогона на целевом
железе). Итоговая таблица дублируется в корневом `README.md`.

| Операция | Хранилище | p50, мс | p95, мс | p99, мс | mean, мс |
| --- | --- | --- | --- | --- | --- |
| read_point | mongo | — | — | — | — |
| read_point | postgres | — | — | — | — |
| read_count | mongo | — | — | — | — |
| read_count | postgres | — | — | — | — |
| read_list | mongo | — | — | — | — |
| read_list | postgres | — | — | — | — |
| write_upsert | mongo | — | — | — | — |
| write_upsert | postgres | — | — | — | — |
| delete | mongo | — | — | — | — |
| delete | postgres | — | — | — | — |

Машиночитаемые результаты сохраняются в `research/storage/results/latest.json`.
