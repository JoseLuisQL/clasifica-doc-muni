"""Rutas de reportes/estadísticas."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import get_current_user, get_db

router = APIRouter(tags=["reports"])


@router.get("/reports/stats")
async def stats(
    desde: date | None = None,
    hasta: date | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    from clasifica.db.models import Documento, JobMigracion

    def _cond(stmt):
        if desde:
            stmt = stmt.where(Documento.cargado_en >= desde)
        if hasta:
            stmt = stmt.where(Documento.cargado_en <= hasta)
        return stmt

    total = (await db.execute(_cond(select(func.count(Documento.id))))).scalar_one()

    async def _group(col):
        rows = (await db.execute(_cond(select(col, func.count(Documento.id))).group_by(col))).all()
        return {str(k): v for k, v in rows if k is not None}

    por_estado = await _group(Documento.estado)
    por_area = await _group(Documento.area_codigo)
    por_tipo = await _group(Documento.tipo_codigo)

    prom_conf = (await db.execute(_cond(select(func.avg(Documento.confianza))))).scalar_one() or 0.0
    migraciones = (
        await db.execute(select(func.count(JobMigracion.id)).where(JobMigracion.estado == "en_curso"))
    ).scalar_one()

    return {
        "total_documentos": total,
        "por_estado": por_estado,
        "por_area": por_area,
        "por_tipo": por_tipo,
        "precision_estimada": round(float(prom_conf), 3),
        "migraciones_activas": migraciones,
    }
