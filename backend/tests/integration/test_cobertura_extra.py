"""Tests adicionales de cobertura de endpoints (migration, reports, listados)."""
import uuid

import pytest


@pytest.mark.asyncio
async def test_estado_job_ok(client, auth_headers, session_factory, monkeypatch):
    monkeypatch.setattr(
        "clasifica.workers.tasks.batch_migration.batch_migration.apply_async", lambda *a, **k: None
    )
    r = await client.post("/api/v1/migration/jobs", json={"ruta_origen": "/z"}, headers=auth_headers)
    jid = r.json()["id"]
    g = await client.get(f"/api/v1/migration/jobs/{jid}", headers=auth_headers)
    assert g.status_code == 200
    assert g.json()["ruta_origen"] == "/z"


@pytest.mark.asyncio
async def test_pausar_job_404(client, auth_headers):
    r = await client.post(f"/api/v1/migration/jobs/{uuid.uuid4()}/pause", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reports_stats_con_grupos(client, auth_headers, session_factory, tmp_path):
    from clasifica.db.models import Documento

    async with session_factory() as s:
        for area, tipo, est in [("GDE", "INF", "clasificado"), ("GIT", "OFI", "clasificado"), ("GDE", "INF", "revision")]:
            s.add(Documento(
                hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex, estado=est,
                ruta_original="x", tamano_bytes=1, area_codigo=area, tipo_codigo=tipo, confianza=0.8,
            ))
        await s.commit()
    resp = await client.get("/api/v1/reports/stats", headers=auth_headers)
    body = resp.json()
    assert body["por_area"].get("GDE", 0) >= 2
    assert body["por_tipo"].get("INF", 0) >= 2
    assert body["por_estado"].get("clasificado", 0) >= 2
    assert body["precision_estimada"] > 0


@pytest.mark.asyncio
async def test_listar_documentos_filtros(client, auth_headers, session_factory):
    from clasifica.db.models import Documento

    async with session_factory() as s:
        s.add(Documento(hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex, estado="clasificado", ruta_original="x", tamano_bytes=1, area_codigo="GDE", tipo_codigo="INF", anio_documento=2026))
        await s.commit()
    r = await client.get("/api/v1/documents", params={"area": "GDE", "tipo": "INF", "anio": 2026}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_suggest_vacio(client, auth_headers):
    r = await client.get("/api/v1/search/suggest", params={"q": "zzz_no_existe"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["asuntos"] == []


def test_anonymize_texto_vacio():
    from clasifica.services.anonymize import anonimizar_texto

    res = anonimizar_texto("")
    assert res.texto == ""
    assert res.patrones_aplicados == {}
