"""Servicio de búsqueda inteligente: full-text + semántica + facetada.

- Full-text: PostgreSQL tsvector (español) + ts_rank_cd.
- Semántica: pgvector, similitud coseno sobre embeddings locales.
- Facetada: filtros por área, tipo, año, fechas, confianza, estado, origen.
- Híbrido: score = α·fulltext_norm + (1-α)·semantica.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Float, and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class FiltrosBusqueda:
    q: str
    modo: str = "hibrido"  # hibrido | exacto | semantico
    area: str | None = None
    tipo: str | None = None
    anio: int | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    confianza_min: float | None = None
    estado: str | None = None
    origen: str | None = None
    alpha: float = 0.5
    limit: int = 20
    offset: int = 0


def _condiciones_facetadas(Documento, f: FiltrosBusqueda) -> list:
    conds = []
    if f.area:
        conds.append(Documento.area_codigo == f.area)
    if f.tipo:
        conds.append(Documento.tipo_codigo == f.tipo)
    if f.anio:
        conds.append(Documento.anio_documento == f.anio)
    if f.fecha_desde:
        conds.append(Documento.cargado_en >= f.fecha_desde)
    if f.fecha_hasta:
        conds.append(Documento.cargado_en <= f.fecha_hasta)
    if f.confianza_min is not None:
        conds.append(Documento.confianza >= f.confianza_min)
    if f.estado:
        conds.append(Documento.estado == f.estado)
    if f.origen:
        conds.append(Documento.origen == f.origen)
    return conds


async def buscar(session: AsyncSession, f: FiltrosBusqueda) -> tuple[list, int]:
    """Ejecuta la búsqueda y devuelve (documentos, total).

    Requiere PostgreSQL (tsvector + pgvector). En modo 'semantico'/'hibrido'
    genera el embedding de la consulta con el servicio local.
    """
    from clasifica.db.models import Documento, DocumentoEmbedding

    conds = _condiciones_facetadas(Documento, f)

    if f.modo == "semantico":
        return await _buscar_semantica(session, f, conds, Documento, DocumentoEmbedding)
    if f.modo == "exacto":
        return await _buscar_fulltext(session, f, conds, Documento)
    return await _buscar_hibrida(session, f, conds, Documento, DocumentoEmbedding)


async def _buscar_fulltext(session, f, conds, Documento) -> tuple[list, int]:
    tsq = func.plainto_tsquery("spanish", f.q)
    rank = func.ts_rank_cd(Documento.search_vector, tsq).label("rank")
    where = and_(Documento.search_vector.op("@@")(tsq), *conds) if f.q else and_(*conds) if conds else text("true")
    stmt = select(Documento).where(where).order_by(rank.desc()).limit(f.limit).offset(f.offset)
    total_stmt = select(func.count()).select_from(Documento).where(where)
    rows = (await session.execute(stmt)).scalars().all()
    total = (await session.execute(total_stmt)).scalar_one()
    return list(rows), total


async def _buscar_semantica(session, f, conds, Documento, DocumentoEmbedding) -> tuple[list, int]:
    from clasifica.services.embeddings import embed_text

    qvec = embed_text(f.q)
    dist = DocumentoEmbedding.vector.cosine_distance(qvec).label("dist")
    where = and_(*conds) if conds else text("true")
    stmt = (
        select(Documento)
        .join(DocumentoEmbedding, DocumentoEmbedding.documento_id == Documento.id)
        .where(where)
        .order_by(dist.asc())
        .limit(f.limit)
        .offset(f.offset)
    )
    total_stmt = (
        select(func.count())
        .select_from(Documento)
        .join(DocumentoEmbedding, DocumentoEmbedding.documento_id == Documento.id)
        .where(where)
    )
    rows = (await session.execute(stmt)).scalars().all()
    total = (await session.execute(total_stmt)).scalar_one()
    return list(rows), total


async def _buscar_hibrida(session, f, conds, Documento, DocumentoEmbedding) -> tuple[list, int]:
    from clasifica.services.embeddings import embed_text

    qvec = embed_text(f.q)
    tsq = func.plainto_tsquery("spanish", f.q)
    rank = func.coalesce(func.ts_rank_cd(Documento.search_vector, tsq), 0.0)
    sim = (1 - DocumentoEmbedding.vector.cosine_distance(qvec)).cast(Float)
    score = (f.alpha * rank + (1 - f.alpha) * sim).label("score")
    where = and_(*conds) if conds else text("true")
    stmt = (
        select(Documento)
        .join(DocumentoEmbedding, DocumentoEmbedding.documento_id == Documento.id, isouter=True)
        .where(where)
        .order_by(score.desc())
        .limit(f.limit)
        .offset(f.offset)
    )
    total_stmt = select(func.count()).select_from(Documento).where(where)
    rows = (await session.execute(stmt)).scalars().all()
    total = (await session.execute(total_stmt)).scalar_one()
    return list(rows), total


async def similares(session: AsyncSession, documento_id, limit: int = 10) -> list[tuple]:
    """Devuelve [(Documento, similitud)] más parecidos por embedding."""
    from clasifica.db.models import Documento, DocumentoEmbedding

    base = await session.get(DocumentoEmbedding, documento_id)
    if base is None:
        return []
    sim = (1 - DocumentoEmbedding.vector.cosine_distance(base.vector)).label("sim")
    stmt = (
        select(Documento, sim)
        .join(DocumentoEmbedding, DocumentoEmbedding.documento_id == Documento.id)
        .where(Documento.id != documento_id)
        .order_by(sim.desc())
        .limit(limit)
    )
    return [(row[0], float(row[1])) for row in (await session.execute(stmt)).all()]


async def sugerencias(session: AsyncSession, q: str) -> dict:
    """Autocompletado: asuntos (trgm), áreas y tipos por prefijo/substring."""
    from clasifica.db.models import Area, Documento, TipoDocumental

    like = f"%{q.lower()}%"
    asuntos = (
        await session.execute(
            select(Documento.asunto)
            .where(func.lower(Documento.asunto).like(like), Documento.asunto.is_not(None))
            .distinct()
            .limit(10)
        )
    ).scalars().all()
    areas = (
        await session.execute(
            select(Area).where(func.lower(Area.nombre).like(like)).limit(10)
        )
    ).scalars().all()
    tipos = (
        await session.execute(
            select(TipoDocumental).where(func.lower(TipoDocumental.nombre).like(like)).limit(10)
        )
    ).scalars().all()
    return {
        "asuntos": [a for a in asuntos if a],
        "areas": [{"codigo": a.codigo, "nombre": a.nombre} for a in areas],
        "tipos": [{"codigo": t.codigo, "nombre": t.nombre} for t in tipos],
    }
