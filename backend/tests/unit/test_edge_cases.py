"""Tests de edge cases (T095): PDF vacío, texto nativo, postprocesado del classifier."""
import pytest

from clasifica.services.classifier import _postprocesar
from clasifica.services.llm_client import ClasificacionLLM
from clasifica.services.ocr import ResultadoOCR


def _ocr(texto="", nativo=True):
    return ResultadoOCR(texto=texto, num_paginas=1, es_nativo=nativo)


def _llm(tipo="INFORME", area="GDE", conf=0.9):
    return ClasificacionLLM(
        tipo_documento=tipo, area=area, asunto="x", anio_documento=2026,
        confianza=conf, justificacion="j",
    )


AREAS = [{"codigo": "GDE", "nombre": "Desarrollo Económico"}, {"codigo": "GRM", "nombre": "Gerencia Municipal"}]
TIPOS = [{"codigo": "INFORME", "nombre": "Informe"}, {"codigo": "OTRO", "nombre": "Otro"}]


def test_confianza_baja_requiere_revision():
    res = _postprocesar(_ocr("texto"), _llm(conf=0.4), {}, AREAS, TIPOS)
    assert res.requiere_revision is True


def test_confianza_alta_no_revision():
    res = _postprocesar(_ocr("texto"), _llm(conf=0.95), {}, AREAS, TIPOS)
    assert res.requiere_revision is False
    assert res.tipo_valido and res.area_valida


def test_tipo_fuera_de_taxonomia_requiere_revision():
    res = _postprocesar(_ocr("t"), _llm(tipo="INEXISTENTE", conf=0.99), {}, AREAS, TIPOS)
    assert res.tipo_valido is False
    assert res.requiere_revision is True


def test_area_fuera_de_taxonomia_requiere_revision():
    res = _postprocesar(_ocr("t"), _llm(area="ZZZ", conf=0.99), {}, AREAS, TIPOS)
    assert res.area_valida is False
    assert res.requiere_revision is True


def test_ocr_detecta_texto_nativo():
    r = _ocr("Este es un informe con texto extraible nativo largo suficiente", nativo=True)
    assert r.es_nativo is True


def test_anonimizacion_multiple_ocurrencias():
    from clasifica.services.anonymize import anonimizar_texto

    texto = "DNI 11111111, DNI 22222222 y otro 33333333"
    res = anonimizar_texto(texto)
    assert res.patrones_aplicados["DNI"] == 3
    assert "11111111" not in res.texto
