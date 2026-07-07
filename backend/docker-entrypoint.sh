#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-api}"

case "$ROLE" in
  api)
    echo "[entrypoint] Aplicando migraciones Alembic..."
    alembic upgrade head
    echo "[entrypoint] Cargando seed (catálogo TUPA + config + admin)..."
    python -m clasifica.db.seeds.loader
    echo "[entrypoint] Iniciando API (uvicorn)..."
    exec uvicorn clasifica.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    echo "[entrypoint] Iniciando worker Celery..."
    exec celery -A clasifica.workers.celery_app.celery_app worker \
      --loglevel=info \
      --concurrency="${CELERY_WORKERS:-4}" \
      -Q interactive,batch,retry
    ;;
  *)
    echo "Rol desconocido: $ROLE (usar: api | worker)"
    exit 1
    ;;
esac
