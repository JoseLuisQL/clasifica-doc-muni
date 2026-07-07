"""Rutas de migración masiva."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.api.deps import get_current_user, get_db
from clasifica.schemas import MigrationJobOut, MigrationRequest

router = APIRouter(prefix="/migration", tags=["migration"])


@router.post("/jobs", response_model=MigrationJobOut, status_code=201)
async def crear_job(
    body: MigrationRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> MigrationJobOut:
    from clasifica.db.models import JobMigracion

    job = JobMigracion(ruta_origen=body.ruta_origen, operador_id=user.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from clasifica.workers.tasks.batch_migration import batch_migration

    batch_migration.apply_async(args=[str(job.id)], queue="batch")
    return MigrationJobOut.model_validate(job)


@router.get("/jobs", response_model=list[MigrationJobOut])
async def listar_jobs(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> list[MigrationJobOut]:
    from clasifica.db.models import JobMigracion

    rows = (await db.execute(select(JobMigracion).order_by(JobMigracion.iniciado_en.desc().nullslast()))).scalars().all()
    return [MigrationJobOut.model_validate(r) for r in rows]


@router.get("/jobs/{job_id}", response_model=MigrationJobOut)
async def estado_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> MigrationJobOut:
    from clasifica.db.models import JobMigracion

    job = await db.get(JobMigracion, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return MigrationJobOut.model_validate(job)


@router.post("/jobs/{job_id}/pause")
async def pausar(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return await _set_estado(db, job_id, "pausado")


@router.post("/jobs/{job_id}/resume")
async def reanudar(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)) -> dict:

    result = await _set_estado(db, job_id, "en_curso")
    # Re-encolar para continuar procesando los restantes
    from clasifica.workers.tasks.batch_migration import batch_migration

    batch_migration.apply_async(args=[str(job_id)], queue="batch")
    return result


async def _set_estado(db: AsyncSession, job_id: uuid.UUID, estado: str) -> dict:
    from clasifica.db.models import JobMigracion

    job = await db.get(JobMigracion, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    job.estado = estado
    await db.commit()
    return {"id": str(job_id), "estado": estado}
