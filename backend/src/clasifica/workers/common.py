"""Utilidades compartidas por las tareas Celery (sesión sync, eventos, progreso)."""
from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from clasifica.config import settings

_engine = None
_SyncSessionFactory: sessionmaker[Session] | None = None
_redis = None


def _get_factory() -> sessionmaker[Session]:
    global _engine, _SyncSessionFactory
    if _SyncSessionFactory is None:
        _engine = create_engine(
            settings.sync_database_url.replace("psycopg2", "psycopg"),
            future=True, pool_pre_ping=True,
        )
        _SyncSessionFactory = sessionmaker(_engine, expire_on_commit=False)
    return _SyncSessionFactory


def SyncSession() -> Session:  # noqa: N802 - fábrica callable, uso como context manager
    return _get_factory()()


def _get_redis():
    global _redis
    if _redis is None:
        import redis

        _redis = redis.Redis.from_url(settings.redis_url)
    return _redis


def registrar_evento(session: Session, documento_id, tipo: str, payload: dict | None = None) -> None:
    from clasifica.db.models import EventoDocumento

    session.add(EventoDocumento(documento_id=documento_id, tipo=tipo, payload=payload or {}))


def publicar_progreso(documento_id: str, evento: dict) -> None:
    """Publica un evento en el canal Redis para el WebSocket del frontend."""
    evento = {**evento, "ts": datetime.now(UTC).isoformat()}
    _get_redis().publish(f"document:{documento_id}:events", json.dumps(evento, ensure_ascii=False))
