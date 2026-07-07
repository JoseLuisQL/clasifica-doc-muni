"""Utilidades compartidas por las tareas Celery (sesión sync, eventos, progreso)."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from clasifica.config import settings

_engine = create_engine(settings.sync_database_url.replace("psycopg2", "psycopg"), future=True, pool_pre_ping=True)
SyncSession: sessionmaker[Session] = sessionmaker(_engine, expire_on_commit=False)
_redis = redis.Redis.from_url(settings.redis_url)


def registrar_evento(session: Session, documento_id, tipo: str, payload: dict | None = None) -> None:
    from clasifica.db.models import EventoDocumento

    session.add(EventoDocumento(documento_id=documento_id, tipo=tipo, payload=payload or {}))


def publicar_progreso(documento_id: str, evento: dict) -> None:
    """Publica un evento en el canal Redis para el WebSocket del frontend."""
    evento = {**evento, "ts": datetime.now(UTC).isoformat()}
    _redis.publish(f"document:{documento_id}:events", json.dumps(evento, ensure_ascii=False))
