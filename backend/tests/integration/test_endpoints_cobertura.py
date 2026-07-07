"""Tests de cobertura de endpoints testeables con SQLite (T102)."""
import io
import uuid

import pytest
from pypdf import PdfWriter


def _pdf() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_auth_refresh(client, auth_headers, client_login_tokens):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": client_login_tokens["refresh_token"]})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_auth_refresh_invalido(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "malo"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_listar_y_detalle_documento(client, auth_headers, session_factory, tmp_path):
    from clasifica.db.models import Documento

    async with session_factory() as s:
        doc = Documento(
            hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex, estado="clasificado",
            ruta_original=str(tmp_path / "x.pdf"), tamano_bytes=10,
            area_codigo="GDE", tipo_codigo="INF", correlativo="0001-GDE-2026-INF",
        )
        s.add(doc)
        await s.commit()
        did = str(doc.id)

    lst = await client.get("/api/v1/documents", params={"estado": "clasificado"}, headers=auth_headers)
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1

    det = await client.get(f"/api/v1/documents/{did}", headers=auth_headers)
    assert det.status_code == 200
    assert det.json()["correlativo"] == "0001-GDE-2026-INF"

    ev = await client.get(f"/api/v1/documents/{did}/events", headers=auth_headers)
    assert ev.status_code == 200


@pytest.mark.asyncio
async def test_detalle_404(client, auth_headers):
    resp = await client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_documento(client, auth_headers, session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr("clasifica.config.settings.data_dir", str(tmp_path))
    from clasifica.db.models import Documento
    from clasifica.services import organizer

    h = uuid.uuid4().hex + uuid.uuid4().hex
    organizer.guardar_original(_pdf(), h)
    async with session_factory() as s:
        doc = Documento(hash_sha256=h, estado="clasificado", ruta_original=str(organizer.ruta_original(h)), tamano_bytes=10)
        s.add(doc)
        await s.commit()
        did = str(doc.id)
    resp = await client.get(f"/api/v1/documents/{did}/preview", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_config_correlativo_get_put(client, auth_headers, session_factory):
    # GET sin config previa devuelve default
    g = await client.get("/api/v1/config/correlativo", headers=auth_headers)
    assert g.status_code == 200
    assert "{SEQ" in g.json()["plantilla"]
    # PUT crea/actualiza
    p = await client.put("/api/v1/config/correlativo", json={"plantilla": "{SEQ:04d}-{TIPO}-{AREA}-{ANIO}"}, headers=auth_headers)
    assert p.status_code == 200


@pytest.mark.asyncio
async def test_config_anonimizacion_get_put(client, auth_headers):
    p = await client.put(
        "/api/v1/config/anonimizacion",
        json={"patrones": [{"nombre": "DNI", "regex": r"\d{8}"}], "redactar_firmas": False},
        headers=auth_headers,
    )
    assert p.status_code == 200
    g = await client.get("/api/v1/config/anonimizacion", headers=auth_headers)
    assert g.json()["redactar_firmas"] is False


@pytest.mark.asyncio
async def test_actualizar_area_y_tipo(client, auth_headers):
    await client.post("/api/v1/config/areas", json={"codigo": "UPD", "nombre": "Original"}, headers=auth_headers)
    r = await client.put("/api/v1/config/areas/UPD", json={"codigo": "UPD", "nombre": "Modificada"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Modificada"
    d = await client.delete("/api/v1/config/areas/UPD", headers=auth_headers)
    assert d.status_code == 204

    await client.post("/api/v1/config/tipos", json={"codigo": "UPT", "nombre": "T"}, headers=auth_headers)
    rt = await client.put("/api/v1/config/tipos/UPT", json={"codigo": "UPT", "nombre": "T2"}, headers=auth_headers)
    assert rt.status_code == 200


@pytest.mark.asyncio
async def test_reports_stats_vacio(client, auth_headers):
    resp = await client.get("/api/v1/reports/stats", headers=auth_headers)
    assert resp.status_code == 200
    assert "total_documentos" in resp.json()


@pytest.mark.asyncio
async def test_reclasificar_reprocesa_llm(client, auth_headers, session_factory, tmp_path, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(
        "clasifica.workers.tasks.process_document.process_document.apply_async",
        lambda *a, **k: calls.__setitem__("n", calls["n"] + 1),
    )
    from clasifica.db.models import Documento

    async with session_factory() as s:
        doc = Documento(hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex, estado="revision", ruta_original="x", tamano_bytes=1)
        s.add(doc)
        await s.commit()
        did = str(doc.id)
    resp = await client.post(f"/api/v1/documents/{did}/classify", json={"reprocesar_llm": True}, headers=auth_headers)
    assert resp.status_code == 200
    assert calls["n"] == 1
