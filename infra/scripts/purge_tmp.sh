#!/usr/bin/env bash
# Purga archivos temporales de OCR/preprocess con más de N días.
set -euo pipefail
DATA_DIR="${DATA_DIR:-/var/clasifica/data}"
DAYS="${1:-7}"

find "$DATA_DIR/tmp/ocr" -type f -mtime "+$DAYS" -delete 2>/dev/null || true
find "$DATA_DIR/tmp/preprocess" -type f -mtime "+$DAYS" -delete 2>/dev/null || true
find "$DATA_DIR/backups" -type f -mtime "+30" -delete 2>/dev/null || true
echo "[purge] tmp purgado (>$DAYS días)"
