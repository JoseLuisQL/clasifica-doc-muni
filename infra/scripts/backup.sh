#!/usr/bin/env bash
# Backup diario: dump de BD + rsync del almacén de documentos.
set -euo pipefail
BACKUP_DIR="${1:-/backup}"
DATE=$(date +%F)
mkdir -p "$BACKUP_DIR"

echo "[backup] pg_dump..."
docker compose -f "$(dirname "$0")/../docker-compose.yml" exec -T db \
  pg_dump -U "${POSTGRES_USER:-clasifica}" "${POSTGRES_DB:-clasifica}" \
  | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

echo "[backup] rsync de documentos..."
rsync -a "${DATA_DIR:-/var/clasifica/data}/" "$BACKUP_DIR/data/"

echo "[backup] Completado en $BACKUP_DIR"
