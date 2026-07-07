"""Schemas Pydantic (DTOs de la API)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    hash_sha256: str
    correlativo: str | None
    estado: str
    tipo_codigo: str | None
    area_codigo: str | None
    asunto: str | None
    anio_documento: int | None
    confianza: float | None
    justificacion_llm: str | None
    num_paginas: int | None
    tamano_bytes: int
    origen: str
    ruta_clasificada: str | None
    cargado_en: datetime
    procesado_en: datetime | None


class PaginatedDocuments(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    documento_id: uuid.UUID
    tipo: str
    timestamp: datetime
    payload: dict


class ClassifyRequest(BaseModel):
    reprocesar_llm: bool = False
    tipo_codigo: str | None = None
    area_codigo: str | None = None
    asunto: str | None = None
    anio_documento: int | None = None
    justificacion_operador: str | None = None


class AreaIn(BaseModel):
    codigo: str
    nombre: str
    padre_codigo: str | None = None
    tipo: str | None = None
    orden: int = 0


class AreaOut(AreaIn):
    model_config = ConfigDict(from_attributes=True)
    activa: bool = True


class TipoIn(BaseModel):
    codigo: str
    nombre: str
    area_tipica_codigo: str | None = None
    descripcion: str | None = None
    palabras_clave: list[str] = []
    plantilla_correlativo: str | None = None


class TipoOut(TipoIn):
    model_config = ConfigDict(from_attributes=True)
    activo: bool = True


class CorrelativoConfig(BaseModel):
    plantilla: str


class LLMConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    endpoint: str
    modelo: str
    temperatura: float
    max_tokens: int
    rate_limit_rpm: int
    timeout_segundos: int
    modelo_embeddings: str
    plantilla_system_prompt: str


class MigrationRequest(BaseModel):
    ruta_origen: str
    prioridad: int = 8


class MigrationJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ruta_origen: str
    total_documentos: int
    procesados: int
    exitosos: int
    en_revision: int
    erroneos: int
    estado: str
    iniciado_en: datetime | None
    finalizado_en: datetime | None


class ExportRequest(BaseModel):
    document_ids: list[uuid.UUID]


class SimilarOut(BaseModel):
    documento: DocumentOut
    similitud: float
