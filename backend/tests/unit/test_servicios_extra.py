"""Tests unitarios adicionales para subir cobertura de lógica pura (T102)."""
import uuid

import pytest

from clasifica.services import organizer
from clasifica.services.dedup import hash_file
from clasifica.services.ocr import ResultadoOCR


def test_hash_file(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"contenido de prueba")
    h1 = hash_file(p)
    assert len(h1) == 64
    p2 = tmp_path / "g.bin"
    p2.write_bytes(b"contenido de prueba")
    assert hash_file(p2) == h1


def test_organizer_guardar_y_ubicar(tmp_path, monkeypatch):
    monkeypatch.setattr("clasifica.config.settings.data_dir", str(tmp_path))
    h = "a" * 64
    orig = organizer.guardar_original(b"%PDF-1.4 data", h)
    assert orig.exists()
    assert orig.name == f"{h}.pdf"
    assert orig.parent.name == "aa" or orig.parent.name == h[2:4]

    dest = organizer.ubicar_clasificado(h, anio=2026, area="GDE", tipo="INF", correlativo="0001-GDE-2026-INF", asunto="prueba de asunto")
    assert dest.exists()
    assert dest.name.startswith("0001-GDE-2026-INF")
    assert "2026" in str(dest) and "GDE" in str(dest) and "INF" in str(dest)


def test_organizer_reubicar(tmp_path, monkeypatch):
    monkeypatch.setattr("clasifica.config.settings.data_dir", str(tmp_path))
    h = "b" * 64
    organizer.guardar_original(b"%PDF-1.4", h)
    d1 = organizer.ubicar_clasificado(h, anio=2026, area="GDE", tipo="INF", correlativo="0001-GDE-2026-INF", asunto="x")
    assert d1.exists()
    d2 = organizer.reubicar(str(d1), hash_sha256=h, anio=2026, area="GIT", tipo="OFI", correlativo="0001-GIT-2026-OFI", asunto="y")
    assert d2.exists()
    assert not d1.exists()  # el viejo se eliminó


def test_ocr_usa_texto_nativo(monkeypatch):
    from clasifica.services import ocr

    monkeypatch.setattr(ocr, "_texto_nativo", lambda b: ("Texto nativo suficientemente largo para superar el umbral", 2))
    monkeypatch.setattr(ocr, "_render_primera_pagina_png", lambda b: b"png")
    res = ocr.procesar_pdf(b"fake")
    assert res.es_nativo is True
    assert res.num_paginas == 2
    assert "nativo" in res.texto


def test_ocr_escaneado_llama_ocr(monkeypatch):
    from clasifica.services import ocr

    monkeypatch.setattr(ocr, "_texto_nativo", lambda b: ("", 1))
    monkeypatch.setattr(ocr, "_render_primera_pagina_png", lambda b: b"png")
    monkeypatch.setattr(ocr, "_ocr_imagen", lambda png: "TEXTO OCR ESCANEADO")
    res = ocr.procesar_pdf(b"fake")
    assert res.es_nativo is False
    assert res.texto == "TEXTO OCR ESCANEADO"


def test_embed_documento_con_mock(monkeypatch):
    from clasifica.services import embeddings

    monkeypatch.setattr(embeddings, "embed_text", lambda t: [0.1, 0.2, 0.3])
    vec = embeddings.embed_documento("asunto", "ocr text")
    assert vec == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_correlativo_async_atomico(session_factory):
    from clasifica.services.correlativo import siguiente_correlativo

    async with session_factory() as s:
        c1 = await siguiente_correlativo(s, area="GDE", anio=2026, tipo="INF")
        c2 = await siguiente_correlativo(s, area="GDE", anio=2026, tipo="INF")
        await s.commit()
    assert c1 == "0001-GDE-2026-INF"
    assert c2 == "0002-GDE-2026-INF"


def test_search_filtros_facetados():
    from clasifica.db.models import Documento
    from clasifica.services.search import FiltrosBusqueda, _condiciones_facetadas

    f = FiltrosBusqueda(q="x", area="GDE", tipo="INF", anio=2026, estado="clasificado", confianza_min=0.5)
    conds = _condiciones_facetadas(Documento, f)
    assert len(conds) == 5  # area, tipo, anio, confianza, estado
