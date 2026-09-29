#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
demo_port=${QUOTEFLOW_PORT:-8080}
docker compose up --build -d
attempt=0
until curl -fsS "http://127.0.0.1:$demo_port/api/health" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    printf 'QuoteFlow did not become healthy within two minutes. Inspect: docker compose logs api web db worker\n' >&2
    exit 1
  fi
  sleep 2
done
printf 'QuoteFlow demo ready: http://localhost:%s\n' "$demo_port"
