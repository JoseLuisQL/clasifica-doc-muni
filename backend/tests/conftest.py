"""Fixtures compartidas para tests de integración con SQLite en memoria."""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clasifica.db.base import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    # SQLite async en archivo temporal (soporta la mayoría del esquema salvo tsvector/vector)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    # Crear solo las tablas que no dependen de tipos PG-only para estos tests
    async with engine.begin() as conn:
        await conn.run_sync(_create_sqlite_schema)
    yield engine
    await engine.dispose()


def _create_sqlite_schema(sync_conn):
    """Crea el esquema en SQLite omitiendo tablas/columnas PG-only."""
    from clasifica.db import models  # noqa: F401

    # Todas las tablas salvo documentos (search_vector computed) y embeddings (vector)
    tablas_ok = [
        Base.metadata.tables[t]
        for t in [
            "usuarios", "areas", "tipos_documentales", "eventos_documento",
            "secuencias_correlativo", "muestras_entrenamiento", "jobs_migracion",
            "configuracion_correlativo", "configuracion_llm", "configuracion_anonimizacion",
        ]
    ]
    Base.metadata.create_all(sync_conn, tables=tablas_ok)
    # documentos sin la columna computed search_vector
    sync_conn.exec_driver_sql(
        """
        CREATE TABLE documentos (
            id CHAR(32) PRIMARY KEY,
            hash_sha256 VARCHAR UNIQUE NOT NULL,
            correlativo VARCHAR,
            estado VARCHAR NOT NULL DEFAULT 'pendiente',
            tipo_codigo VARCHAR,
            area_codigo VARCHAR,
            asunto TEXT,
            anio_documento INTEGER,
            confianza FLOAT,
            justificacion_llm TEXT,
            ocr_text TEXT,
            ruta_original TEXT NOT NULL,
            ruta_clasificada TEXT,
            num_paginas INTEGER,
            tamano_bytes BIGINT NOT NULL,
            origen VARCHAR NOT NULL DEFAULT 'interactivo',
            prioridad INTEGER NOT NULL DEFAULT 5,
            operador_id CHAR(32),
            cargado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            procesado_en TIMESTAMP,
            version_config INTEGER NOT NULL DEFAULT 1,
            search_vector TEXT
        )
        """
    )


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_factory, monkeypatch):
    from clasifica.api import deps
    from clasifica.core.security import hash_password
    from clasifica.db.models import Usuario
    from clasifica.main import app

    async def _get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[deps.get_db] = _get_db

    # Crear admin
    async with session_factory() as s:
        s.add(Usuario(username="admin", password_hash=hash_password("admin"), nombre_completo="Admin"))
        await s.commit()

    # No encolar en Celery real
    monkeypatch.setattr(
        "clasifica.workers.tasks.process_document.process_document.apply_async",
        lambda *a, **k: None,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
