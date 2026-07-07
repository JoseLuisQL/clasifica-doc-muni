"""Tests unitarios de servicios core que no requieren BD ni OCR pesado."""
from clasifica.services.anonymize import anonimizar_texto
from clasifica.services.correlativo import render_correlativo, slugify_asunto
from clasifica.services.dedup import hash_bytes
from clasifica.services.embeddings import cosine_similarity


def test_dedup_hash_estable():
    assert hash_bytes(b"hola") == hash_bytes(b"hola")
    assert hash_bytes(b"hola") != hash_bytes(b"chau")
    assert len(hash_bytes(b"x")) == 64


def test_anonimizar_dni_ruc_email():
    texto = "El ciudadano con DNI 12345678 y RUC 20123456789, correo juan@muni.gob.pe"
    res = anonimizar_texto(texto)
    assert "12345678" not in res.texto
    assert "20123456789" not in res.texto
    assert "juan@muni.gob.pe" not in res.texto
    assert res.patrones_aplicados.get("DNI", 0) >= 1
    assert res.patrones_aplicados.get("RUC", 0) >= 1
    assert res.patrones_aplicados.get("EMAIL", 0) >= 1


def test_anonimizar_ruc_no_es_partido_por_dni():
    # RUC de 11 dígitos no debe convertirse en [DNI] + resto
    res = anonimizar_texto("RUC 20123456789 fin")
    assert "[RUC]" in res.texto
    assert "[DNI]" not in res.texto


def test_correlativo_seq_al_inicio():
    corr = render_correlativo("{SEQ:04d}-{AREA}-{ANIO}-{TIPO}", seq=1, area="GDE", anio=2026, tipo="INF")
    assert corr == "0001-GDE-2026-INF"
    assert corr.startswith("0001")


def test_correlativo_acepta_alias_anio():
    corr = render_correlativo("{SEQ:04d}-{AREA}-{AÑO}-{TIPO}", seq=42, area="GIT", anio=2026, tipo="LED")
    assert corr == "0042-GIT-2026-LED"


def test_slugify_asunto():
    assert slugify_asunto("Informe sobre Licencia de Construcción") == "informe-sobre-licencia-de-construccion"
    assert slugify_asunto("") == "sin-asunto"
    assert len(slugify_asunto("a" * 200)) <= 60


def test_cosine_similarity():
    assert cosine_similarity([1, 0], [1, 0]) == 1.0
    assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9
    assert cosine_similarity([], [1]) == 0.0
