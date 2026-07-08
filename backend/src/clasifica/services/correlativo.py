"""Asignación atómica de correlativo y render de plantilla.

El correlativo usa la secuencia AL INICIO por defecto:
    {SEQ:04d}-{AREA}-{ANIO}-{TIPO}  ->  0001-GDE-2026-INF

La asignación de la secuencia es atómica vía ``INSERT ... ON CONFLICT
DO UPDATE ... RETURNING`` (PostgreSQL) — libre de race conditions incluso
cuando dos workers procesan en paralelo documentos con la misma
(área, año, tipo) que aún no tiene fila en ``secuencias_correlativo``.
El ``SELECT ... FOR UPDATE`` anterior no protegía el caso en que la fila
no existe (ambos workers ven None → ambos INSERT → UniqueViolation).
"""
from __future__ import annotations

import re

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from clasifica.db.models import SecuenciaCorrelativo


def render_correlativo(plantilla: str, *, seq: int, area: str, anio: int, tipo: str) -> str:
    """Renderiza la plantilla. Soporta {SEQ}, {SEQ:04d}, {AREA}, {ANIO}, {TIPO}.

    También acepta {AÑO} como alias de {ANIO} para comodidad.
    """
    plantilla = plantilla.replace("{AÑO}", "{ANIO}").replace("{AÑO:", "{ANIO:")
    return plantilla.format(SEQ=seq, AREA=area, ANIO=anio, TIPO=tipo)


async def siguiente_correlativo(
    session: AsyncSession,
    *,
    area: str,
    anio: int,
    tipo: str,
    plantilla: str = "{SEQ:04d}-{AREA}-{ANIO}-{TIPO}",
) -> str:
    """Asigna el siguiente correlativo de forma atómica y devuelve el string.

    Usa SELECT FOR UPDATE para bloquear la fila (área, año, tipo) hasta el commit.
    El llamador es responsable de commitear la transacción.
    """
    stmt = (
        select(SecuenciaCorrelativo)
        .where(
            SecuenciaCorrelativo.area_codigo == area,
            SecuenciaCorrelativo.anio == anio,
            SecuenciaCorrelativo.tipo_codigo == tipo,
        )
        .with_for_update()
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = SecuenciaCorrelativo(area_codigo=area, anio=anio, tipo_codigo=tipo, ultimo_valor=1)
        session.add(row)
    else:
        row.ultimo_valor += 1
    await session.flush()
    return render_correlativo(plantilla, seq=row.ultimo_valor, area=area, anio=anio, tipo=tipo)


def siguiente_correlativo_sync(
    session,
    *,
    area: str,
    anio: int,
    tipo: str,
    plantilla: str = "{SEQ:04d}-{AREA}-{ANIO}-{TIPO}",
) -> str:
    """Asigna el siguiente correlativo de forma atómica (sesión síncrona, worker).

    Usa ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING`` para que la
    creación+incremento de la secuencia sea una sola operación atómica a
    nivel de fila, evitando el race condition TOCTOU del patrón
    SELECT-then-INSERT cuando dos workers procesan en paralelo documentos
    con la misma (área, año, tipo) que aún no tiene fila.
    """
    sql = text(
        """
        INSERT INTO secuencias_correlativo (area_codigo, anio, tipo_codigo, ultimo_valor)
        VALUES (:area, :anio, :tipo, 1)
        ON CONFLICT (area_codigo, anio, tipo_codigo)
        DO UPDATE SET ultimo_valor = secuencias_correlativo.ultimo_valor + 1
        RETURNING ultimo_valor
        """
    )
    result = session.execute(sql, {"area": area, "anio": anio, "tipo": tipo})
    nuevo_seq = result.scalar_one()
    return render_correlativo(plantilla, seq=nuevo_seq, area=area, anio=anio, tipo=tipo)


def slugify_asunto(asunto: str | None, max_len: int = 60) -> str:
    """Convierte un asunto en slug para el nombre de archivo (sin acentos, guiones)."""
    if not asunto:
        return "sin-asunto"
    import unicodedata

    txt = unicodedata.normalize("NFKD", asunto).encode("ascii", "ignore").decode("ascii")
    txt = txt.lower()
    txt = re.sub(r"[^a-z0-9]+", "-", txt).strip("-")
    return txt[:max_len].rstrip("-") or "sin-asunto"
