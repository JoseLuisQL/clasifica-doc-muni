"""Rutas de documentos: upload, detalle, preview, clasificar, eventos, revisión."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import Paginacion, get_current_user, get_db
from clasifica.schemas import (
    ClassifyRequest,
    DocumentOut,
    EventOut,
    PaginatedDocuments,
)
from clasifica.services import organizer
from clasifica.services.dedup import hash_bytes

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def subir_documento(
    file: UploadFile = File(...),
    origen: str = Form("interactivo"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> DocumentOut:
    from clasifica.db.models import Documento, EventoDocumento

    data = await file.read()
    if not data or not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se requiere un PDF no vacío")
    h = hash_bytes(data)

    existing = (
        await db.execute(select(Documento).where(Documento.hash_sha256 == h))
    ).scalar_one_or_none()
    if existing:
        return DocumentOut.model_validate(existing)

    organizer.guardar_original(data, h)
    doc = Documento(
        hash_sha256=h,
        estado="pendiente",
        ruta_original=str(organizer.ruta_original(h)),
        tamano_bytes=len(data),
        origen=origen,
        prioridad=1 if origen == "interactivo" else 8,
        operador_id=user.id,
    )
    db.add(doc)
    await db.flush()
    db.add(EventoDocumento(documento_id=doc.id, tipo="cargado", payload={"origen": origen, "filename": file.filename}))
    await db.commit()
    await db.refresh(doc)

    # Encolar procesamiento
    from clasifica.workers.tasks.process_document import process_document

    queue = "interactive" if origen == "interactivo" else "batch"
    process_document.apply_async(args=[str(doc.id)], queue=queue)

    return DocumentOut.model_validate(doc)


@router.get("", response_model=PaginatedDocuments)
async def listar_documentos(
    estado: str | None = None,
    area: str | None = None,
    tipo: str | None = None,
    anio: int | None = None,
    pag: Paginacion = Depends(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> PaginatedDocuments:
    from clasifica.db.models import Documento

    stmt = select(Documento)
    count_stmt = select(func.count(Documento.id))
    filtros = []
    if estado:
        filtros.append(Documento.estado == estado)
    if area:
        filtros.append(Documento.area_codigo == area)
    if tipo:
        filtros.append(Documento.tipo_codigo == tipo)
    if anio:
        filtros.append(Documento.anio_documento == anio)
    for f in filtros:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Documento.cargado_en.desc()).offset(pag.offset).limit(pag.page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return PaginatedDocuments(
        items=[DocumentOut.model_validate(r) for r in rows],
        total=total, page=pag.page, page_size=pag.page_size,
    )


@router.get("/review", response_model=PaginatedDocuments)
async def bandeja_revision(
    pag: Paginacion = Depends(), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> PaginatedDocuments:
    from clasifica.db.models import Documento

    base = select(Documento).where(Documento.estado == "revision")
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(base.order_by(Documento.cargado_en.desc()).offset(pag.offset).limit(pag.page_size))
    ).scalars().all()
    return PaginatedDocuments(
        items=[DocumentOut.model_validate(r) for r in rows], total=total, page=pag.page, page_size=pag.page_size
    )


@router.get("/{documento_id}", response_model=DocumentOut)
async def detalle(documento_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> DocumentOut:
    from clasifica.db.models import Documento

    doc = await db.get(Documento, documento_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return DocumentOut.model_validate(doc)


@router.get("/{documento_id}/events", response_model=list[EventOut])
async def eventos(documento_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[EventOut]:
    from clasifica.db.models import EventoDocumento

    rows = (
        await db.execute(
            select(EventoDocumento)
            .where(EventoDocumento.documento_id == documento_id)
            .order_by(EventoDocumento.timestamp.desc())
        )
    ).scalars().all()
    return [EventOut.model_validate(r) for r in rows]


@router.get("/{documento_id}/preview")
async def preview(documento_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    from clasifica.db.models import Documento

    doc = await db.get(Documento, documento_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return FileResponse(doc.ruta_original, media_type="application/pdf", filename=f"{doc.correlativo or doc.hash_sha256[:12]}.pdf")


@router.post("/{documento_id}/classify", response_model=DocumentOut)
async def clasificar_manual(
    documento_id: uuid.UUID,
    body: ClassifyRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> DocumentOut:
    from clasifica.db.models import Documento, EventoDocumento, MuestraEntrenamiento
    from clasifica.services.correlativo import siguiente_correlativo

    doc = await db.get(Documento, documento_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="No encontrado")

    if body.reprocesar_llm:
        from clasifica.workers.tasks.process_document import process_document

        doc.estado = "pendiente"
        await db.commit()
        process_document.apply_async(args=[str(doc.id)], queue="interactive")
        await db.refresh(doc)
        return DocumentOut.model_validate(doc)

    # Corrección manual: registrar muestra de entrenamiento
    tipo_ant, area_ant = doc.tipo_codigo, doc.area_codigo
    nuevo_tipo = body.tipo_codigo or doc.tipo_codigo
    nueva_area = body.area_codigo or doc.area_codigo
    if body.asunto is not None:
        doc.asunto = body.asunto
    if body.anio_documento is not None:
        doc.anio_documento = body.anio_documento

    cambio_clasif = (nuevo_tipo != tipo_ant) or (nueva_area != area_ant)
    doc.tipo_codigo = nuevo_tipo
    doc.area_codigo = nueva_area

    # Recalcular correlativo si cambió área/tipo/año o si no tenía
    from clasifica.db.models import ConfiguracionCorrelativo

    cfg = await db.get(ConfiguracionCorrelativo, 1)
    plantilla = cfg.plantilla if cfg else "{SEQ:04d}-{AREA}-{ANIO}-{TIPO}"
    anio = doc.anio_documento or datetime.now(UTC).year
    if cambio_clasif or not doc.correlativo:
        vieja_ruta = doc.ruta_clasificada
        doc.correlativo = await siguiente_correlativo(
            db, area=doc.area_codigo, anio=anio, tipo=doc.tipo_codigo, plantilla=plantilla
        )
        dest = organizer.reubicar(
            vieja_ruta, hash_sha256=doc.hash_sha256, anio=anio, area=doc.area_codigo,
            tipo=doc.tipo_codigo, correlativo=doc.correlativo, asunto=doc.asunto,
        )
        doc.ruta_clasificada = str(dest)

    doc.estado = "clasificado"
    doc.procesado_en = datetime.now(UTC)
    db.add(EventoDocumento(documento_id=doc.id, tipo="corregido", payload={
        "tipo": {"antes": tipo_ant, "ahora": nuevo_tipo},
        "area": {"antes": area_ant, "ahora": nueva_area},
        "operador_id": str(user.id),
    }))
    if cambio_clasif:
        db.add(MuestraEntrenamiento(
            documento_id=doc.id, tipo_original=tipo_ant, area_original=area_ant,
            tipo_corregido=nuevo_tipo, area_corregida=nueva_area, operador_id=user.id,
            justificacion_operador=body.justificacion_operador,
        ))
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)
