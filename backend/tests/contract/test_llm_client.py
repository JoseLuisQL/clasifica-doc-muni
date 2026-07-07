"""Test contract del cliente LLM contra un mock server (pytest-httpserver)."""
import json

import pytest

from clasifica.services.llm_client import LLMClient, LLMError

AREAS = [{"codigo": "GDE", "nombre": "Gerencia de Desarrollo Económico"}]
TIPOS = [{"codigo": "INF", "nombre": "Informe"}]


@pytest.mark.asyncio
async def test_llm_respuesta_valida(httpserver):
    respuesta = {
        "choices": [{"message": {"content": json.dumps({
            "tipo_documento": "INFORME", "area": "GDE",
            "asunto": "Solicitud de informe", "anio_documento": 2026,
            "confianza": 0.92, "justificacion": "Encabezado INFORME",
        })}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }
    httpserver.expect_request("/chat/completions", method="POST").respond_with_json(respuesta)
    client = LLMClient(endpoint=httpserver.url_for(""), api_key="test", timeout=5, max_retries=1)
    res = await client.clasificar(ocr_text="INFORME N 001", areas=AREAS, tipos=TIPOS)
    assert res.tipo_documento == "INFORME"
    assert res.area == "GDE"
    assert res.confianza == 0.92
    assert res.tokens_input == 100


@pytest.mark.asyncio
async def test_llm_reintenta_en_500(httpserver):
    httpserver.expect_request("/chat/completions", method="POST").respond_with_data(
        "err", status=500
    )
    client = LLMClient(endpoint=httpserver.url_for(""), api_key="t", timeout=2, max_retries=2)
    with pytest.raises(LLMError):
        await client.clasificar(ocr_text="x", areas=AREAS, tipos=TIPOS)


@pytest.mark.asyncio
async def test_llm_json_malformado_falla_controlado(httpserver):
    httpserver.expect_request("/chat/completions", method="POST").respond_with_json(
        {"choices": [{"message": {"content": "no es json {"}}], "usage": {}}
    )
    client = LLMClient(endpoint=httpserver.url_for(""), api_key="t", timeout=2, max_retries=1)
    with pytest.raises(LLMError):
        await client.clasificar(ocr_text="x", areas=AREAS, tipos=TIPOS)
