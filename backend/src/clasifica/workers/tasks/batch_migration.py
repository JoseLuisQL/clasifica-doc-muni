"""Tarea batch_migration: recorre una carpeta y encola cada PDF."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from clasifica.services import organizer
from clasifica.services.dedup import hash_file
from clasifica.workers.celery_app import celery_app
from clasifica.workers.common import SyncSession, registrar_evento


@celery_app.task(name="clasifica.batch_migration", bind=True)
def batch_migration(self, job_id: str) -> dict:
    from clasifica.db.models import Documento, JobMigracion
    from clasifica.workers.tasks.process_document import process_document

    with SyncSession() as session:
        job = session.get(JobMigracion, uuid.UUID(job_id))
        if job is None:
            return {"error": "job no encontrado"}
        carpeta = Path(job.ruta_origen)
        pdfs = sorted(carpeta.rglob("*.pdf")) if carpeta.exists() else []
        job.total_documentos = len(pdfs)
        job.estado = "en_curso"
        job.iniciado_en = datetime.now(UTC)
        session.commit()

        for pdf_path in pdfs:
            session.refresh(job)
            if job.estado == "pausado":
                break
            try:
                data = pdf_path.read_bytes()
                h = hash_file(pdf_path)
                existing = session.query(Documento).filter_by(hash_sha256=h).first()
                if existing:
                    job.procesados += 1
                    session.commit()
                    continue
                organizer.guardar_original(data, h)
                doc = Documento(
                    hash_sha256=h, estado="pendiente", ruta_original=str(organizer.ruta_original(h)),
                    tamano_bytes=len(data), origen="migracion", prioridad=8,
                    operador_id=job.operador_id,
                )
                session.add(doc)
                session.flush()
                registrar_evento(session, doc.id, "cargado", {"origen": "migracion", "job": job_id})
                session.commit()
                process_document.apply_async(args=[str(doc.id), job_id], queue="batch")
                job.procesados += 1
                session.commit()
            except Exception:  # noqa: BLE001
                job.erroneos += 1
                session.commit()

        session.refresh(job)
        if job.estado != "pausado":
            job.estado = "completado"
            job.finalizado_en = datetime.now(UTC)
            session.commit()
        return {"estado": job.estado, "procesados": job.procesados}
