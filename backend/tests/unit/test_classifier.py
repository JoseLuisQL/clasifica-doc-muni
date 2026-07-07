"""Tests del orquestador classifier con LLM mockeado (async + sync)."""
import pytest

from clasifica.services import classifier
from clasifica.services.llm_client import ClasificacionLLM

AREAS = [{"codigo": "GDE", "nombre": "Desarrollo Económico"}, {"codigo": "GRM", "nombre": "Gerencia Municipal"}]
TIPOS = [{"codigo": "INFORME", "nombre": "Informe"}, {"codigo": "OTRO", "nombre": "Otro"}]


class _FakeLLM:
    def __init__(self, conf=0.9):
        self._conf = conf

    async def clasificar(self, **kwargs):
        return ClasificacionLLM(
            tipo_documento="INFORME", area="GDE", asunto="asunto de prueba",
            anio_documento=2026, confianza=self._conf, justificacion="ok",
            tokens_input=10, tokens_output=5, latency_ms=100,
        )


@pytest.mark.asyncio
async def test_clasificar_pdf_async(monkeypatch):
    monkeypatch.setattr(
        classifier, "procesar_pdf",
        lambda b: __import__("clasifica.services.ocr", fromlist=["ResultadoOCR"]).ResultadoOCR(
            texto="INFORME con DNI 12345678", num_paginas=1, es_nativo=True
        ),
    )
    res = await classifier.clasificar_pdf_async(
        b"fake", areas=AREAS, tipos=TIPOS, llm_client=_FakeLLM(conf=0.95)
    )
    assert res.llm.tipo_documento == "INFORME"
    assert res.requiere_revision is False
    # el DNI debe haberse anonimizado antes del LLM
    assert res.patrones_anonimizados.get("DNI", 0) == 1


@pytest.mark.asyncio
async def test_clasificar_pdf_async_baja_confianza(monkeypatch):
    from clasifica.services.ocr import ResultadoOCR

    monkeypatch.setattr(classifier, "procesar_pdf", lambda b: ResultadoOCR(texto="x", num_paginas=1, es_nativo=True))
    res = await classifier.clasificar_pdf_async(b"f", areas=AREAS, tipos=TIPOS, llm_client=_FakeLLM(conf=0.3))
    assert res.requiere_revision is True


def test_clasificar_pdf_sync(monkeypatch):
    from clasifica.services.ocr import ResultadoOCR

    monkeypatch.setattr(classifier, "procesar_pdf", lambda b: ResultadoOCR(texto="informe", num_paginas=1, es_nativo=True))
    res = classifier.clasificar_pdf(b"f", areas=AREAS, tipos=TIPOS, llm_client=_FakeLLM(conf=0.9))
    assert res.llm.area == "GDE"


def test_errors_jerarquia():
    from clasifica.core.errors import (
        ClasificaError,
        DocumentoInvalido,
        LLMNoDisponible,
        TaxonomiaError,
    )

    assert issubclass(DocumentoInvalido, ClasificaError)
    assert issubclass(TaxonomiaError, ClasificaError)
    assert issubclass(LLMNoDisponible, ClasificaError)


def test_ocr_render_falla_no_rompe(monkeypatch):
    from clasifica.services import ocr

    monkeypatch.setattr(ocr, "_texto_nativo", lambda b: ("texto nativo largo suficiente para el umbral minimo", 1))

    def _boom(b):
        raise RuntimeError("render falló")

    monkeypatch.setattr(ocr, "_render_primera_pagina_png", _boom)
    res = ocr.procesar_pdf(b"fake")
    assert res.primera_pagina_png_b64 is None
    assert res.es_nativo is True
