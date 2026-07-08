"""Cliente para el LLM multimodal (Qware, OpenAI-compatible).

Implementa el contrato de contracts/llm-contract.md: response_format
json_schema, retries con backoff, timeout, y parseo/validación de la
respuesta contra el schema de clasificación.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass

import httpx

from clasifica.config import settings

TIPOS_ENUM = [
    "INFORME", "MEMORANDO", "OFICIO", "CARTA", "RESOLUCION", "ORDENANZA",
    "DECRETO", "TUPA", "ACTA", "DENUNCIA", "OTRO",
]

DEFAULT_SYSTEM_PROMPT = (
    "Eres un archivero experto en gestión documental de municipalidades "
    "distritales del Perú. Recibes el texto OCR (anonimizado) y la imagen de "
    "la primera página de un documento institucional escaneado. Clasifícalo "
    "devolviendo EXCLUSIVAMENTE un JSON con: tipo_documento (código de la "
    "taxonomía vigente o OTRO), area (código de la taxonomía vigente), asunto "
    "(máx 200 chars, neutro), anio_documento (año del documento), confianza "
    "(0..1) y justificacion. Usa SOLO códigos de la taxonomía proporcionada."
)

_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tipo_documento", "area", "asunto", "anio_documento", "confianza", "justificacion"],
    "properties": {
        "tipo_documento": {"type": "string"},
        "area": {"type": "string"},
        "asunto": {"type": "string"},
        "anio_documento": {"type": "integer"},
        "confianza": {"type": "number"},
        "justificacion": {"type": "string"},
    },
}


@dataclass
class ClasificacionLLM:
    tipo_documento: str
    area: str
    asunto: str
    anio_documento: int
    confianza: float
    justificacion: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0


class LLMError(Exception):
    pass


_FENCE_RE = re.compile(r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _parse_json_content(content: str | None) -> dict:
    """Parsea el JSON devuelto por el LLM, tolerante a fences de markdown.

    Algunos proveedores OpenAI-compatible (incluido Qware) envuelven el JSON
    en bloques ```json ... ``` aunque se pida response_format json_schema, o
    devuelven texto extra alrededor. Esto extrae y parsea el JSON de forma
    robusta para no fallar con 'Expecting value: line 1 column 1 (char 0)'.
    """
    if not content:
        raise ValueError("respuesta LLM vacía")
    txt = content.strip()
    # 1) Fence completo: ```json\n{...}\n```
    m = _FENCE_RE.match(txt)
    if m:
        txt = m.group(1).strip()
    # 2) Si aún hay fence parcial o texto extra, tomar el primer bloque {...}
    if not txt.startswith("{"):
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            txt = txt[start : end + 1]
    return json.loads(txt)


class LLMClient:
    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        max_retries: int = 3,
    ) -> None:
        self.endpoint = (endpoint or settings.llm_endpoint).rstrip("/")
        self.model = model or settings.llm_model
        self.api_key = api_key or settings.llm_api_key
        self.timeout = timeout or settings.llm_timeout_segundos
        self.max_retries = max_retries

    def _build_messages(
        self, ocr_text: str, areas: list[dict], tipos: list[dict], image_b64: str | None, system_prompt: str
    ) -> list[dict]:
        areas_txt = "\n".join(f"{a['codigo']}: {a['nombre']}" for a in areas)
        tipos_txt = "\n".join(f"{t['codigo']}: {t['nombre']}" for t in tipos)
        user_content: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"Clasifica el siguiente documento municipal. Texto OCR (anonimizado):\n\n"
                    f"---\n{ocr_text[:24000]}\n---\n\n"
                    f"Taxonomía vigente de áreas (código: nombre):\n{areas_txt}\n\n"
                    f"Taxonomía vigente de tipos (código: nombre):\n{tipos_txt}"
                ),
            }
        ]
        if image_b64:
            user_content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "low"}}
            )
        return [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def _payload(self, messages: list[dict]) -> dict:
        return {
            "model": self.model,
            "temperature": settings.llm_temperatura,
            "max_tokens": settings.llm_max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "clasificacion_documento", "strict": True, "schema": _JSON_SCHEMA},
            },
            "messages": messages,
        }

    async def clasificar(
        self,
        *,
        ocr_text: str,
        areas: list[dict],
        tipos: list[dict],
        image_b64: str | None = None,
        system_prompt: str = "",
    ) -> ClasificacionLLM:
        messages = self._build_messages(ocr_text, areas, tipos, image_b64, system_prompt)
        payload = self._payload(messages)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.endpoint}/chat/completions"

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    import time

                    t0 = time.monotonic()
                    resp = await client.post(url, json=payload, headers=headers)
                    latency = int((time.monotonic() - t0) * 1000)
                    if resp.status_code == 429 or resp.status_code >= 500:
                        raise LLMError(f"HTTP {resp.status_code}")
                    if resp.status_code >= 400:
                        raise LLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = _parse_json_content(content)
                    usage = data.get("usage", {})
                    return self._to_result(parsed, usage, latency)
                except (httpx.HTTPError, LLMError, KeyError, ValueError) as exc:
                    last_exc = exc
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(min(2**attempt * 2, 60))
        raise LLMError(f"LLM falló tras {self.max_retries} intentos: {last_exc}")

    @staticmethod
    def _to_result(parsed: dict, usage: dict, latency: int) -> ClasificacionLLM:
        tipo = str(parsed.get("tipo_documento") or parsed.get("tipo") or "OTRO").upper()
        return ClasificacionLLM(
            tipo_documento=tipo,
            area=str(parsed.get("area", "")),
            asunto=str(parsed.get("asunto", ""))[:200],
            anio_documento=int(parsed.get("anio_documento", 0) or 0),
            confianza=float(parsed.get("confianza", 0.0) or 0.0),
            justificacion=str(parsed.get("justificacion", "")),
            tokens_input=int(usage.get("prompt_tokens", 0)),
            tokens_output=int(usage.get("completion_tokens", 0)),
            latency_ms=latency,
        )
