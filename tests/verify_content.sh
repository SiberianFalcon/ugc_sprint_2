#!/usr/bin/env bash
# Сквозная проверка сервиса контента: ugc + MongoDB.
# Запускать из корня репозитория: sudo bash tests/verify_content.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

wait_health() {
  local svc="$1" tries="${2:-60}" cid st
  for i in $(seq 1 "$tries"); do
    cid=$(docker compose ps -q "$svc" 2>/dev/null)
    st=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null)
    if [ "$st" = "healthy" ]; then
      echo "$svc healthy (~$((i*2))s)"
      return 0
    fi
    sleep 2
  done
  echo "WARN: $svc not healthy in time"
  return 1
}

echo "############ CLEAN PREVIOUS STATE ############"
docker compose down -v --remove-orphans || true

echo "############ BUILD & UP (mongo + ugc) ############"
docker compose up -d --build ugc
echo "compose up exit=$?"

echo "############ WAIT FOR MONGO ############"
wait_health mongo

echo "############ CONTAINERS ############"
docker compose ps

echo "############ WAIT FOR UGC ############"
for i in $(seq 1 30); do
  if curl -sf http://localhost:8001/health/live >/dev/null 2>&1; then
    echo "ugc live (~$((i*2))s)"
    break
  fi
  sleep 2
done

echo "############ HEALTH ############"
echo -n "live:  "; curl -s http://localhost:8001/health/live; echo
echo -n "ready: "; curl -s http://localhost:8001/health/ready; echo

echo "############ LIKE ############"
echo -n "put like: "; curl -s -o /dev/null -w '%{http_code}' -X PUT http://localhost:8001/api/v1/likes/film-1; echo
echo -n "status:  "; curl -s http://localhost:8001/api/v1/likes/film-1; echo

echo "############ BOOKMARK ############"
echo -n "put bookmark: "; curl -s -o /dev/null -w '%{http_code}' -X PUT http://localhost:8001/api/v1/bookmarks/film-1; echo
echo -n "status:       "; curl -s http://localhost:8001/api/v1/bookmarks/film-1; echo

echo "############ REVIEW ############"
echo -n "create: "; curl -s -X POST http://localhost:8001/api/v1/reviews \
  -H 'Content-Type: application/json' \
  -d '{"film_id":"film-1","rating":8,"text":"Отличный фильм"}'; echo
echo -n "list:   "; curl -s "http://localhost:8001/api/v1/reviews?film_id=film-1"; echo
echo -n "bad rating http code: "; curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8001/api/v1/reviews \
  -H 'Content-Type: application/json' -d '{"film_id":"film-1","rating":11,"text":"x"}'; echo

echo "############ MY LIKES ############"
echo -n "my likes: "; curl -s http://localhost:8001/api/v1/likes; echo

echo "############ DONE ############"
echo "Остановить: sudo docker compose down"
echo "Остановить с данными: sudo docker compose down -v"
