"""Modelos ORM (SQLAlchemy 2.0 declarativo) — 12 modelos del dominio.

Reflejan el esquema creado por la migración Alembic
``alembic/versions/0001_inicial.py``. Se registran sobre ``Base.metadata``
(importándolos aquí) para que Alembic y el seed los vean.

Notas de portabilidad:
- UUIDs con el tipo genérico ``sqlalchemy.Uuid`` (en PG → UUID, en SQLite →
  CHAR(32)) para que los tests con SQLite funcionen sin pgcrypto.
- JSON con ``sqlalchemy.JSON`` (en PG lee/escribe columnas JSONB sin problema;
  en SQLite se almacena como TEXT). La migración crea las columnas como JSONB.
- ``Documento.search_vector`` (TSVECTOR computed) y ``DocumentoEmbedding.vector``
  (pgvector) son tipos PG-only; los tests con SQLite excluyen esas tablas de
  ``create_all`` (ver ``tests/conftest.py``), así que nunca se compilan ahí.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from clasifica.db.base import Base

# pgvector es dependencia del proyecto. En tests SQLite la tabla embeddings
# se excluye de create_all (conftest), por lo que Vector nunca se compila ahí.
# Respaldo a Float si pgvector no estuviera disponible.
try:  # pragma: no cover - depende del entorno
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - respaldo sin pgvector
    from sqlalchemy import Float as _Float

    class Vector(_Float):  # type: ignore[override]
        """Respaldo sin pgvector: acepta dim como arg ignorado."""

        def __init__(self, dim=None, *args, **kwargs):  # noqa: D401
            super().__init__(*args, **kwargs)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Usuario(Base):
    """Usuario del sistema (MVP: único admin, preparado para RBAC)."""

    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String, nullable=False)
    rol: Mapped[str] = mapped_column(String, nullable=False, default="admin", server_default="admin")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Area(Base):
    """Área orgánica de la municipalidad (catálogo TUPA, jerárquica)."""

    __tablename__ = "areas"

    codigo: Mapped[str] = mapped_column(String, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    padre_codigo: Mapped[str | None] = mapped_column(
        String, ForeignKey("areas.codigo"), nullable=True
    )
    tipo: Mapped[str | None] = mapped_column(String, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TipoDocumental(Base):
    """Tipo documental del catálogo TUPA (editable)."""

    __tablename__ = "tipos_documentales"

    codigo: Mapped[str] = mapped_column(String, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    area_tipica_codigo: Mapped[str | None] = mapped_column(
        String, ForeignKey("areas.codigo"), nullable=True
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    palabras_clave: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    plantilla_correlativo: Mapped[str | None] = mapped_column(String, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Documento(Base):
    """Documento PDF cargado: OCR, clasificación LLM y organización física."""

    __tablename__ = "documentos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    hash_sha256: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    correlativo: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="pendiente", server_default="pendiente")
    tipo_codigo: Mapped[str | None] = mapped_column(
        String, ForeignKey("tipos_documentales.codigo"), nullable=True
    )
    area_codigo: Mapped[str | None] = mapped_column(
        String, ForeignKey("areas.codigo"), nullable=True
    )
    asunto: Mapped[str | None] = mapped_column(Text, nullable=True)
    anio_documento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confianza: Mapped[float | None] = mapped_column(Float, nullable=True)
    justificacion_llm: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ruta_original: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_clasificada: Mapped[str | None] = mapped_column(Text, nullable=True)
    num_paginas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    origen: Mapped[str] = mapped_column(String, nullable=False, default="interactivo", server_default="interactivo")
    prioridad: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    operador_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    cargado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    procesado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version_config: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # Columna computada PG-only (tsvector). Excluida en tests SQLite (conftest).
    search_vector = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('spanish', coalesce(asunto,'')), 'A') || "
            "setweight(to_tsvector('spanish', coalesce(ocr_text,'')), 'B')",
            persisted=True,
        ),
        nullable=True,
    )


class EventoDocumento(Base):
    """Evento de ciclo de vida de un documento (auditoría)."""

    __tablename__ = "eventos_documento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")


class SecuenciaCorrelativo(Base):
    """Contador atómico de correlativos por (área, año, tipo)."""

    __tablename__ = "secuencias_correlativo"

    area_codigo: Mapped[str] = mapped_column(String, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_codigo: Mapped[str] = mapped_column(String, primary_key=True)
    ultimo_valor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class MuestraEntrenamiento(Base):
    """Corrección del operador que alimenta el feedback loop (reentrenamiento)."""

    __tablename__ = "muestras_entrenamiento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False
    )
    tipo_original: Mapped[str | None] = mapped_column(String, nullable=True)
    area_original: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo_corregido: Mapped[str] = mapped_column(String, nullable=False)
    area_corregida: Mapped[str] = mapped_column(String, nullable=False)
    operador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    justificacion_operador: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usada_en_reentrenamiento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    version_modelo: Mapped[str | None] = mapped_column(String, nullable=True)


class DocumentoEmbedding(Base):
    """Embedding semántico (384-dim) de un documento para búsqueda híbrida."""

    __tablename__ = "documentos_embeddings"

    documento_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documentos.id", ondelete="CASCADE"), primary_key=True
    )
    vector: Mapped[list] = mapped_column(Vector(384), nullable=False)
    modelo: Mapped[str] = mapped_column(String, nullable=False)
    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobMigracion(Base):
    """Job de migración masiva de documentos históricos."""

    __tablename__ = "jobs_migracion"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    ruta_origen: Mapped[str] = mapped_column(Text, nullable=False)
    total_documentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    procesados: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    exitosos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    en_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    erroneos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    estado: Mapped[str] = mapped_column(String, nullable=False, default="encolado", server_default="encolado")
    iniciado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )


class ConfiguracionCorrelativo(Base):
    """Singleton (id=1): plantilla de correlativo configurable."""

    __tablename__ = "configuracion_correlativo"
    __table_args__ = (CheckConstraint("id = 1", name="ck_correlativo_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plantilla: Mapped[str] = mapped_column(
        String, nullable=False, default="{SEQ:04d}-{AREA}-{ANIO}-{TIPO}",
        server_default="{SEQ:04d}-{AREA}-{ANIO}-{TIPO}",
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConfiguracionLLM(Base):
    """Singleton (id=1): configuración del LLM y embeddings."""

    __tablename__ = "configuracion_llm"
    __table_args__ = (CheckConstraint("id = 1", name="ck_llm_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(
        String, nullable=False, default="https://api.qware.me/v1",
        server_default="https://api.qware.me/v1",
    )
    modelo: Mapped[str] = mapped_column(
        String, nullable=False, default="gemini-3-flash-agent", server_default="gemini-3-flash-agent"
    )
    api_key_secret_ref: Mapped[str] = mapped_column(
        String, nullable=False, default="LLM_API_KEY", server_default="LLM_API_KEY"
    )
    temperatura: Mapped[float] = mapped_column(Float, nullable=False, default=0.1, server_default="0.1")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=600, server_default="600")
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    timeout_segundos: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    modelo_embeddings: Mapped[str] = mapped_column(
        String, nullable=False, default="paraphrase-multilingual-MiniLM-L12-v2",
        server_default="paraphrase-multilingual-MiniLM-L12-v2",
    )
    plantilla_system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConfiguracionAnonimizacion(Base):
    """Singleton (id=1): patrones de anonimización PII."""

    __tablename__ = "configuracion_anonimizacion"
    __table_args__ = (CheckConstraint("id = 1", name="ck_anon_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patrones: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    redactar_firmas: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# Asignar el tipo pgvector Vector(384) a DocumentoEmbedding.vector.
# pgvector es dependencia del proyecto; en tests SQLite la tabla embeddings
# se excluye de create_all (conftest), por lo que este tipo nunca se compila
# allí. Si pgvector no estuviera instalado, cae a Float como respaldo.


__all__ = [
    "Area",
    "ConfiguracionAnonimizacion",
    "ConfiguracionCorrelativo",
    "ConfiguracionLLM",
    "Documento",
    "DocumentoEmbedding",
    "EventoDocumento",
    "JobMigracion",
    "MuestraEntrenamiento",
    "SecuenciaCorrelativo",
    "TipoDocumental",
    "Usuario",
]
