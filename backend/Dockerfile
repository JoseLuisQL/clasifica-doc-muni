FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Dependencias del sistema para OCR (PaddleOCR/OpenCV) y PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 poppler-utils curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[ocr]"

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh && pip install -e .

EXPOSE 8000

ENTRYPOINT []
CMD ["./docker-entrypoint.sh", "api"]
