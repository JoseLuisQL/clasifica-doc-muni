"""Integration test US1: login, upload, detalle, corrección manual."""
import io

import pytest
from pypdf import PdfWriter


def _pdf_bytes() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_login_ok(client):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_falla_credenciales(client):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "mala"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_crea_documento_pendiente(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr("clasifica.config.settings.data_dir", str(tmp_path))
    files = {"file": ("informe.pdf", _pdf_bytes(), "application/pdf")}
    resp = await client.post("/api/v1/documents", files=files, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["estado"] == "pendiente"
    assert body["origen"] == "interactivo"
    assert len(body["hash_sha256"]) == 64


@pytest.mark.asyncio
async def test_upload_deduplica_por_hash(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr("clasifica.config.settings.data_dir", str(tmp_path))
    pdf = _pdf_bytes()
    files = {"file": ("a.pdf", pdf, "application/pdf")}
    r1 = await client.post("/api/v1/documents", files=files, headers=auth_headers)
    files = {"file": ("b.pdf", pdf, "application/pdf")}
    r2 = await client.post("/api/v1/documents", files=files, headers=auth_headers)
    assert r1.json()["id"] == r2.json()["id"]  # mismo hash → mismo documento


@pytest.mark.asyncio
async def test_upload_rechaza_no_pdf(client, auth_headers):
    files = {"file": ("x.txt", b"hola", "text/plain")}
    resp = await client.post("/api/v1/documents", files=files, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_sin_auth_401(client):
    files = {"file": ("x.pdf", _pdf_bytes(), "application/pdf")}
    resp = await client.post("/api/v1/documents", files=files)
    assert resp.status_code == 401
