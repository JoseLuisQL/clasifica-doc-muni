"""Integration test US3: bandeja de revisión y corrección con feedback loop."""
import uuid

import pytest
from sqlalchemy import select


async def _crear_doc_revision(session_factory, tmp_path):
    """Inserta un documento en estado revisión + área/tipo semilla."""
    from clasifica.db.models import Area, Documento, TipoDocumental

    async with session_factory() as s:
        s.add(Area(codigo="GDE", nombre="Desarrollo Económico"))
        s.add(Area(codigo="GIT", nombre="Infraestructura"))
        s.add(TipoDocumental(codigo="INF", nombre="Informe"))
        s.add(TipoDocumental(codigo="OFI", nombre="Oficio"))
        doc = Documento(
            hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            estado="revision", ruta_original=str(tmp_path / "x.pdf"),
            tamano_bytes=100, tipo_codigo="INF", area_codigo="GDE",
            asunto="dudoso", anio_documento=2026, confianza=0.4,
        )
        s.add(doc)
        await s.commit()
        return str(doc.id)


@pytest.mark.asyncio
async def test_bandeja_revision_lista(client, auth_headers, session_factory, tmp_path):
    await _crear_doc_revision(session_factory, tmp_path)
    resp = await client.get("/api/v1/documents/review", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert all(d["estado"] == "revision" for d in resp.json()["items"])


@pytest.mark.asyncio
async def test_correccion_registra_muestra_y_reubica(client, auth_headers, session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr("clasifica.config.settings.data_dir", str(tmp_path))
    # crear original físico para el hardlink
    doc_id = await _crear_doc_revision(session_factory, tmp_path)
    from clasifica.db.models import Documento
    from clasifica.services import organizer

    async with session_factory() as s:
        doc = await s.get(Documento, uuid.UUID(doc_id))
        organizer.guardar_original(b"%PDF-1.4 test", doc.hash_sha256)
        doc.ruta_original = str(organizer.ruta_original(doc.hash_sha256))
        await s.commit()

    # Corregir: cambiar tipo INF->OFI y area GDE->GIT
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/classify",
        json={"tipo_codigo": "OFI", "area_codigo": "GIT", "justificacion_operador": "es un oficio"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estado"] == "clasificado"
    assert body["tipo_codigo"] == "OFI"
    assert body["area_codigo"] == "GIT"
    assert body["correlativo"].startswith("0001-GIT-2026-OFI")

    # Verificar que se registró la MuestraEntrenamiento
    from clasifica.db.models import MuestraEntrenamiento

    async with session_factory() as s:
        muestras = (await s.execute(select(MuestraEntrenamiento))).scalars().all()
        assert len(muestras) == 1
        assert muestras[0].tipo_original == "INF"
        assert muestras[0].tipo_corregido == "OFI"
        assert muestras[0].area_corregida == "GIT"
