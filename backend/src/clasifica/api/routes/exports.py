"""Rutas de exportación (ZIP+CSV)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import get_current_user, get_db
from clasifica.schemas import ExportRequest
from clasifica.services.exporter import exportar_zip

router = APIRouter(tags=["exports"])


@router.post("/exports")
async def exportar(
    body: ExportRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> Response:
    from clasifica.db.models import Documento

    rows = (
        await db.execute(select(Documento).where(Documento.id.in_(body.document_ids)))
    ).scalars().all()
    docs = [
        {
            "correlativo": d.correlativo, "tipo_codigo": d.tipo_codigo, "area_codigo": d.area_codigo,
            "asunto": d.asunto, "anio_documento": d.anio_documento, "confianza": d.confianza,
            "estado": d.estado, "cargado_en": str(d.cargado_en),
            "ruta_clasificada": d.ruta_clasificada, "ruta_original": d.ruta_original,
        }
        for d in rows
    ]
    contenido = exportar_zip(docs)
    return Response(
        content=contenido,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=export_clasifica.zip"},
    )
