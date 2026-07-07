"""Orquestador de clasificación: OCR -> anonimización -> LLM -> postprocesado."""
from __future__ import annotations

from dataclasses import dataclass

from clasifica.config import settings
from clasifica.services.anonymize import anonimizar_texto
from clasifica.services.llm_client import ClasificacionLLM, LLMClient
from clasifica.services.ocr import ResultadoOCR, procesar_pdf


@dataclass
class ResultadoClasificacion:
    ocr: ResultadoOCR
    llm: ClasificacionLLM
    patrones_anonimizados: dict[str, int]
    requiere_revision: bool
    tipo_valido: bool
    area_valida: bool


def clasificar_pdf(
    pdf_bytes: bytes,
    *,
    areas: list[dict],
    tipos: list[dict],
    system_prompt: str = "",
    patrones_anon: list[dict] | None = None,
    llm_client: LLMClient | None = None,
) -> ResultadoClasificacion:
    """Ejecuta el pipeline completo de clasificación de un PDF."""
    ocr = procesar_pdf(pdf_bytes)
    anon = anonimizar_texto(ocr.texto, patrones_anon)

    client = llm_client or LLMClient()
    import asyncio

    llm = asyncio.run(
        client.clasificar(
            ocr_text=anon.texto,
            areas=areas,
            tipos=tipos,
            image_b64=ocr.primera_pagina_png_b64,
            system_prompt=system_prompt,
        )
    )
    return _postprocesar(ocr, llm, anon.patrones_aplicados, areas, tipos)


async def clasificar_pdf_async(
    pdf_bytes: bytes,
    *,
    areas: list[dict],
    tipos: list[dict],
    system_prompt: str = "",
    patrones_anon: list[dict] | None = None,
    llm_client: LLMClient | None = None,
) -> ResultadoClasificacion:
    ocr = procesar_pdf(pdf_bytes)
    anon = anonimizar_texto(ocr.texto, patrones_anon)
    client = llm_client or LLMClient()
    llm = await client.clasificar(
        ocr_text=anon.texto,
        areas=areas,
        tipos=tipos,
        image_b64=ocr.primera_pagina_png_b64,
        system_prompt=system_prompt,
    )
    return _postprocesar(ocr, llm, anon.patrones_aplicados, areas, tipos)


def _postprocesar(
    ocr: ResultadoOCR,
    llm: ClasificacionLLM,
    patrones: dict[str, int],
    areas: list[dict],
    tipos: list[dict],
) -> ResultadoClasificacion:
    codigos_area = {a["codigo"] for a in areas}
    codigos_tipo = {t["codigo"] for t in tipos}
    tipo_valido = llm.tipo_documento in codigos_tipo
    area_valida = llm.area in codigos_area
    requiere_revision = (
        llm.confianza < settings.umbral_confianza or not tipo_valido or not area_valida
    )
    return ResultadoClasificacion(
        ocr=ocr,
        llm=llm,
        patrones_anonimizados=patrones,
        requiere_revision=requiere_revision,
        tipo_valido=tipo_valido,
        area_valida=area_valida,
    )
