"""Integration/unit test US4: exporter, sugerencias, stats."""
import io
import uuid
import zipfile

import pytest
from sqlalchemy import select

from clasifica.services.exporter import exportar_zip


def test_exporter_zip_con_csv(tmp_path):
    pdf = tmp_path / "0001-GDE-2026-INF-x.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    docs = [{
        "correlativo": "0001-GDE-2026-INF", "tipo_codigo": "INF", "area_codigo": "GDE",
        "asunto": "prueba", "anio_documento": 2026, "confianza": 0.9, "estado": "clasificado",
        "cargado_en": "2026-01-01", "ruta_clasificada": str(pdf),
    }]
    data = exportar_zip(docs)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        nombres = zf.namelist()
        assert "metadatos.csv" in nombres
        assert any(n.endswith("0001-GDE-2026-INF.pdf") for n in nombres)
        csv_content = zf.read("metadatos.csv").decode()
        assert "0001-GDE-2026-INF" in csv_content


@pytest.mark.asyncio
async def test_sugerencias(client, auth_headers, session_factory):
    from clasifica.db.models import Area, TipoDocumental

    async with session_factory() as s:
        s.add(Area(codigo="GDE", nombre="Gerencia de Desarrollo Económico"))
        s.add(TipoDocumental(codigo="INF", nombre="Informe"))
        await s.commit()
    resp = await client.get("/api/v1/search/suggest", params={"q": "desarrollo"}, headers=auth_headers)
    assert resp.status_code == 200
    assert any("Desarrollo" in a["nombre"] for a in resp.json()["areas"])


@pytest.mark.asyncio
async def test_stats(client, auth_headers, session_factory, tmp_path):
    from clasifica.db.models import Documento

    async with session_factory() as s:
        for i in range(3):
            s.add(Documento(
                hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex, estado="clasificado",
                ruta_original=str(tmp_path / f"{i}.pdf"), tamano_bytes=10,
                area_codigo="GDE", tipo_codigo="INF", confianza=0.9,
            ))
        await s.commit()
    resp = await client.get("/api/v1/reports/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_documentos"] >= 3
    assert body["por_estado"].get("clasificado", 0) >= 3


@pytest.mark.asyncio
async def test_export_endpoint(client, auth_headers, session_factory, tmp_path, monkeypatch):
    from clasifica.db.models import Documento

    pdf = tmp_path / "orig.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    async with session_factory() as s:
        doc = Documento(
            hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex, estado="clasificado",
            ruta_original=str(pdf), ruta_clasificada=str(pdf), tamano_bytes=10,
            correlativo="0001-GDE-2026-INF", area_codigo="GDE", tipo_codigo="INF",
        )
        s.add(doc)
        await s.commit()
        doc_id = str(doc.id)
    resp = await client.post("/api/v1/exports", json={"document_ids": [doc_id]}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
