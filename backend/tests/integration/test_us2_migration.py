"""Integration test US2: crear job de migración, pausar, reanudar."""
import pytest


@pytest.mark.asyncio
async def test_crear_job_migracion(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "clasifica.workers.tasks.batch_migration.batch_migration.apply_async",
        lambda *a, **k: None,
    )
    resp = await client.post(
        "/api/v1/migration/jobs", json={"ruta_origen": "/data/historico"}, headers=auth_headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["ruta_origen"] == "/data/historico"
    assert body["estado"] == "encolado"


@pytest.mark.asyncio
async def test_pausar_y_reanudar_job(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "clasifica.workers.tasks.batch_migration.batch_migration.apply_async",
        lambda *a, **k: None,
    )
    r = await client.post("/api/v1/migration/jobs", json={"ruta_origen": "/x"}, headers=auth_headers)
    job_id = r.json()["id"]

    rp = await client.post(f"/api/v1/migration/jobs/{job_id}/pause", headers=auth_headers)
    assert rp.status_code == 200
    assert rp.json()["estado"] == "pausado"

    rr = await client.post(f"/api/v1/migration/jobs/{job_id}/resume", headers=auth_headers)
    assert rr.status_code == 200
    assert rr.json()["estado"] == "en_curso"


@pytest.mark.asyncio
async def test_estado_job_404(client, auth_headers):
    import uuid

    resp = await client.get(f"/api/v1/migration/jobs/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_listar_jobs(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "clasifica.workers.tasks.batch_migration.batch_migration.apply_async",
        lambda *a, **k: None,
    )
    await client.post("/api/v1/migration/jobs", json={"ruta_origen": "/a"}, headers=auth_headers)
    resp = await client.get("/api/v1/migration/jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
