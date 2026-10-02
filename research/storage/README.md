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
| read_point | mongo | 0.769 | 1.263 | 1.578 | 0.803 |
| read_point | postgres | 0.400 | 0.767 | 0.857 | 0.456 |
| read_count | mongo | 0.537 | 0.808 | 0.883 | 0.558 |
| read_count | postgres | 1.016 | 21.296 | 24.443 | 6.551 |
| read_list | mongo | 0.467 | 0.866 | 1.858 | 0.533 |
| read_list | postgres | 0.227 | 0.514 | 1.722 | 0.289 |
| write_upsert | mongo | 1.046 | 1.601 | 1.831 | 1.074 |
| write_upsert | postgres | 1.300 | 2.173 | 3.065 | 1.440 |
| delete | mongo | 1.258 | 1.784 | 2.084 | 1.269 |
| delete | postgres | 1.070 | 1.724 | 2.364 | 1.168 |

Обе базы укладываются в требование чтения < 200 мс. На точечном чтении
PostgreSQL немного быстрее, но на подсчёте лайков фильма MongoDB
существенно стабильнее (p95 0.8 мс против 21.3 мс у PostgreSQL). С учётом
гибкой схемы рецензий и идемпотентных upsert выбор сделан в пользу MongoDB.

Машиночитаемые результаты сохраняются в `research/storage/results/latest.json`.
