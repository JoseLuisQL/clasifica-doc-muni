"""Integration test US5: configuración de taxonomía, correlativo, export/import."""
import pytest


@pytest.mark.asyncio
async def test_crear_area_y_tipo(client, auth_headers):
    ra = await client.post(
        "/api/v1/config/areas", json={"codigo": "GMA", "nombre": "Gerencia de Medio Ambiente"}, headers=auth_headers
    )
    assert ra.status_code == 201, ra.text
    rt = await client.post(
        "/api/v1/config/tipos",
        json={"codigo": "CHB2", "nombre": "Constancia de Habitabilidad", "area_tipica_codigo": "GMA"},
        headers=auth_headers,
    )
    assert rt.status_code == 201, rt.text
    # Listar
    lst = await client.get("/api/v1/config/areas", headers=auth_headers)
    assert any(a["codigo"] == "GMA" for a in lst.json())


@pytest.mark.asyncio
async def test_area_duplicada_409(client, auth_headers):
    await client.post("/api/v1/config/areas", json={"codigo": "DUP", "nombre": "X"}, headers=auth_headers)
    r2 = await client.post("/api/v1/config/areas", json={"codigo": "DUP", "nombre": "Y"}, headers=auth_headers)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_actualizar_correlativo(client, auth_headers):
    r = await client.put(
        "/api/v1/config/correlativo", json={"plantilla": "MUNI-{SEQ:05d}-{AREA}-{ANIO}-{TIPO}"}, headers=auth_headers
    )
    assert r.status_code == 200
    g = await client.get("/api/v1/config/correlativo", headers=auth_headers)
    assert g.json()["plantilla"] == "MUNI-{SEQ:05d}-{AREA}-{ANIO}-{TIPO}"


@pytest.mark.asyncio
async def test_export_config_yaml(client, auth_headers):
    await client.post("/api/v1/config/areas", json={"codigo": "EXP", "nombre": "Exportable"}, headers=auth_headers)
    r = await client.get("/api/v1/config/export", headers=auth_headers)
    assert r.status_code == 200
    assert "EXP" in r.text
    assert "areas" in r.text


@pytest.mark.asyncio
async def test_import_config(client, auth_headers):
    body = {
        "areas": [{"codigo": "IMP1", "nombre": "Importada"}],
        "tipos": [{"codigo": "IMPT", "nombre": "Tipo Importado"}],
    }
    r = await client.post("/api/v1/config/import", json=body, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["areas"] == 1
    assert r.json()["tipos"] == 1
