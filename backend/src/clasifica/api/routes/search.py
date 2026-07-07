"""Rutas de búsqueda inteligente: search, similar, suggest."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import get_current_user, get_db
from clasifica.schemas import DocumentOut, PaginatedDocuments, SimilarOut
from clasifica.services.search import FiltrosBusqueda, buscar, similares, sugerencias

router = APIRouter(tags=["search"])


@router.get("/documents/search", response_model=PaginatedDocuments)
async def search(
    q: str,
    modo: str = "hibrido",
    area: str | None = None,
    tipo: str | None = None,
    anio: int | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    confianza_min: float | None = None,
    estado: str | None = None,
    origen: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> PaginatedDocuments:
    f = FiltrosBusqueda(
        q=q, modo=modo, area=area, tipo=tipo, anio=anio,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        confianza_min=confianza_min, estado=estado, origen=origen,
        limit=page_size, offset=(max(1, page) - 1) * page_size,
    )
    rows, total = await buscar(db, f)
    return PaginatedDocuments(
        items=[DocumentOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size
    )


@router.get("/documents/{documento_id}/similar", response_model=list[SimilarOut])
async def get_similares(
    documento_id: uuid.UUID, limit: int = 10, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> list[SimilarOut]:
    pares = await similares(db, documento_id, limit)
    return [SimilarOut(documento=DocumentOut.model_validate(d), similitud=s) for d, s in pares]


@router.get("/search/suggest")
async def suggest(q: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return await sugerencias(db, q)
