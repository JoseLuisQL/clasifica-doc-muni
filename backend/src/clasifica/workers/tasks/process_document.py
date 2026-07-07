"""Tarea process_document: pipeline completo de un documento."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from clasifica.config import settings
from clasifica.services import embeddings as emb_svc
from clasifica.services import organizer
from clasifica.services.classifier import clasificar_pdf
from clasifica.services.correlativo import render_correlativo
from clasifica.workers.celery_app import celery_app
from clasifica.workers.common import SyncSession, publicar_progreso, registrar_evento


def _taxonomia(session) -> tuple[list[dict], list[dict]]:
    from clasifica.db.models import Area, TipoDocumental

    areas = [
        {"codigo": a.codigo, "nombre": a.nombre}
        for a in session.execute(select(Area).where(Area.activa.is_(True))).scalars()
    ]
    tipos = [
        {"codigo": t.codigo, "nombre": t.nombre}
        for t in session.execute(select(TipoDocumental).where(TipoDocumental.activo.is_(True))).scalars()
    ]
    return areas, tipos


@celery_app.task(name="clasifica.process_document", bind=True, max_retries=3)
def process_document(self, documento_id: str) -> dict:
    from clasifica.db.models import (
        ConfiguracionAnonimizacion,
        ConfiguracionCorrelativo,
        ConfiguracionLLM,
        Documento,
    )

    with SyncSession() as session:
        doc = session.get(Documento, uuid.UUID(documento_id))
        if doc is None:
            return {"error": "documento no encontrado"}

        doc.estado = "procesando"
        registrar_evento(session, doc.id, "procesando")
        session.commit()
        publicar_progreso(documento_id, {"estado": "procesando"})

        pdf_bytes = organizer.ruta_original(doc.hash_sha256).read_bytes()
        areas, tipos = _taxonomia(session)
        cfg_llm = session.get(ConfiguracionLLM, 1)
        cfg_anon = session.get(ConfiguracionAnonimizacion, 1)
        cfg_corr = session.get(ConfiguracionCorrelativo, 1)
        system_prompt = cfg_llm.plantilla_system_prompt if cfg_llm else ""
        patrones = cfg_anon.patrones if cfg_anon else None

        try:
            res = clasificar_pdf(
                pdf_bytes, areas=areas, tipos=tipos,
                system_prompt=system_prompt, patrones_anon=patrones,
            )
        except Exception as exc:  # noqa: BLE001
            doc.estado = "error"
            registrar_evento(session, doc.id, "error", {"detalle": str(exc)[:500]})
            session.commit()
            publicar_progreso(documento_id, {"estado": "error", "detalle": str(exc)[:200]})
            return {"estado": "error"}

        registrar_evento(session, doc.id, "llm_llamada", {
            "modelo": res.llm and settings.llm_model,
            "tokens_input": res.llm.tokens_input, "tokens_output": res.llm.tokens_output,
            "latency_ms": res.llm.latency_ms,
        })
        registrar_evento(session, doc.id, "anon_fin", {"patrones": res.patrones_anonimizados})

        doc.ocr_text = res.ocr.texto
        doc.num_paginas = res.ocr.num_paginas
        doc.asunto = res.llm.asunto
        doc.confianza = res.llm.confianza
        doc.justificacion_llm = res.llm.justificacion
        doc.anio_documento = res.llm.anio_documento or datetime.now(UTC).year
        doc.tipo_codigo = res.llm.tipo_documento if res.tipo_valido else "OTRO"
        doc.area_codigo = res.llm.area if res.area_valida else "GRM"

        if res.requiere_revision:
            doc.estado = "revision"
            registrar_evento(session, doc.id, "revision", {"confianza": res.llm.confianza})
            session.commit()
            publicar_progreso(documento_id, {"estado": "revision", "confianza": res.llm.confianza})
            return {"estado": "revision"}

        # Asignar correlativo atómico (sync SELECT FOR UPDATE)
        from clasifica.db.models import SecuenciaCorrelativo

        plantilla = cfg_corr.plantilla if cfg_corr else "{SEQ:04d}-{AREA}-{ANIO}-{TIPO}"
        seq_row = session.execute(
            select(SecuenciaCorrelativo)
            .where(
                SecuenciaCorrelativo.area_codigo == doc.area_codigo,
                SecuenciaCorrelativo.anio == doc.anio_documento,
                SecuenciaCorrelativo.tipo_codigo == doc.tipo_codigo,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if seq_row is None:
            seq_row = SecuenciaCorrelativo(
                area_codigo=doc.area_codigo, anio=doc.anio_documento,
                tipo_codigo=doc.tipo_codigo, ultimo_valor=1,
            )
            session.add(seq_row)
        else:
            seq_row.ultimo_valor += 1
        session.flush()
        doc.correlativo = render_correlativo(
            plantilla, seq=seq_row.ultimo_valor, area=doc.area_codigo,
            anio=doc.anio_documento, tipo=doc.tipo_codigo,
        )
        registrar_evento(session, doc.id, "correlativo_asignado", {"correlativo": doc.correlativo})

        dest = organizer.ubicar_clasificado(
            doc.hash_sha256, anio=doc.anio_documento, area=doc.area_codigo,
            tipo=doc.tipo_codigo, correlativo=doc.correlativo, asunto=doc.asunto,
        )
        doc.ruta_clasificada = str(dest)
        registrar_evento(session, doc.id, "movido", {"ruta": str(dest)})

        # Embedding semántico
        try:
            vec = emb_svc.embed_documento(doc.asunto, doc.ocr_text)
            from clasifica.db.models import DocumentoEmbedding

            existing = session.get(DocumentoEmbedding, doc.id)
            if existing:
                existing.vector = vec
            else:
                session.add(DocumentoEmbedding(documento_id=doc.id, vector=vec, modelo=settings.embedding_model))
        except Exception:  # noqa: BLE001 - embedding best-effort
            pass

        doc.estado = "clasificado"
        doc.procesado_en = datetime.now(UTC)
        registrar_evento(session, doc.id, "clasificado", {"correlativo": doc.correlativo})
        session.commit()
        publicar_progreso(documento_id, {
            "estado": "clasificado", "correlativo": doc.correlativo,
            "tipo": doc.tipo_codigo, "area": doc.area_codigo, "asunto": doc.asunto,
        })
        return {"estado": "clasificado", "correlativo": doc.correlativo}
