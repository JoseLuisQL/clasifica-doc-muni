# LLM Contract — Clasificación de Documentos Municipales

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07

Contrato de la interacción con el LLM multimodal vía API OpenAI-compatible.
El cliente `backend/src/clasifica/services/llm_client.py` y el orquestador
`classifier.py` DEBEN cumplir este contrato; los tests de contrato lo
validan con un mock server.

## Endpoint

Proveedor concreto: **Qware** (`https://api.qware.me/v1`), modelo
**`gemini-3-flash-agent`** (multimodal). API OpenAI-compatible.
Verificado 2026-07-07: `/v1/models` lista el modelo; `/v1/chat/completions`
responde correctamente; `/v1/embeddings` devuelve 404 (los embeddings se
generan localmente, ver `research.md` §11).

`POST {LLM_ENDPOINT}/chat/completions`

Default: `POST https://api.qware.me/v1/chat/completions`

Headers:
```
Authorization: Bearer {LLM_API_KEY}     # secret en variable de entorno, nunca en código
Content-Type: application/json
```

## Request body

Modelo por defecto: `gemini-3-flash-agent` (Qware). `response_format`
json_schema es respetado por el proveedor (verificado).

```json
{
  "model": "gemini-3-flash-agent",
  "temperature": 0.1,
  "max_tokens": 600,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "clasificacion_documento",
      "strict": true,
      "schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["tipo_documento", "area", "asunto", "anio_documento", "confianza", "justificacion"],
        "properties": {
          "tipo_documento": {
            "type": "string",
            "enum": ["INFORME", "MEMORANDO", "OFICIO", "CARTA", "RESOLUCION", "ORDENANZA", "DECRETO", "TUPA", "ACTA", "DENUNCIA", "OTRO"]
          },
          "area": { "type": "string", "description": "código de área de la taxonomía vigente, ej: GER-DES" },
          "asunto": { "type": "string", "maxLength": 200 },
          "anio_documento": { "type": "integer", "minimum": 1990, "maximum": 2100 },
          "confianza": { "type": "number", "minimum": 0, "maximum": 1 },
          "justificacion": { "type": "string", "maxLength": 500 }
        }
      }
    }
  },
  "messages": [
    {
      "role": "system",
      "content": "{SYSTEM_PROMPT_VIGENTE}"
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Clasifica el siguiente documento municipal. Texto OCR (anonimizado):\n\n---\n{OCR_TEXT_TRUNCADO_6K_TOKENS}\n---\n\nTaxonomía vigente de áreas:\n{AREAS_JSON}\nTaxonomía vigente de tipos:\n{TIPOS_JSON}"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,{PRIMERA_PAGINA_BASE64}",
            "detail": "low"
          }
        }
      ]
    }
  ]
}
```

## System prompt (plantilla por defecto)

```
Eres un archivero experto en gestión documental de municipalidades
distritales del Perú. Recibes el texto OCR (anonimizado) y la imagen de
la primera página de un documento institucional escaneado.

Tu tarea es clasificarlo devolviendo EXCLUSIVAMENTE un JSON con:
- tipo_documento: uno de los códigos de la taxonomía vigente (o OTRO si
  ninguno encaja).
- area: el código de área de la taxonomía vigente que mejor corresponda.
- asunto: descripción corta del tema (máx 200 caracteres), en español.
- anio_documento: año que aparece en el documento (no el actual).
- confianza: tu nivel de certeza entre 0 y 1.
- justificacion: breve explicación de tu clasificación.

Reglas:
- Usa SOLO códigos de la taxonomía vigente proporcionada.
- Si el documento mezcla tipos (ej. oficio con anexo de informe),
  clasifica por la portada y nota en justificacion.
- El asunto debe ser neutro y descriptivo, no copiar texto literal.
- Si no puedes determinar un campo, pon confianza baja (<0.5) y
  justificacion explicando la ambigüedad.
```

La plantilla se almacena en `configuracion_llm.plantilla_system_prompt`
y es editable vía UI.

## Response (esperada)

```json
{
  "id": "chatcmpl-...",
  "model": "gpt-4o-mini",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "{\"tipo_documento\":\"INFORME\",\"area\":\"GER-DES\",\"asunto\":\"Solicitud de informacion sobre licencias de funcionamiento\",\"anio_documento\":2026,\"confianza\":0.92,\"justificacion\":\"Documento con encabezado INFORME dirigido a la Gerencia de Desarrollo Economico.\"}"
    },
    "finish_reason": "stop"
  }],
  "usage": { "prompt_tokens": 1850, "completion_tokens": 80, "total_tokens": 1930 }
}
```

El cliente parsea `choices[0].message.content` como JSON y lo valida
contra el schema Pydantic `ClasificacionLLM`.

## Manejo de errores

| Condición | Acción |
|-----------|--------|
| HTTP 429 (rate limit) | Esperar `Retry-After` o backoff exponencial (base 2s, max 60s), hasta 3 reintentos |
| HTTP 5xx | Reintento con backoff, hasta 3 |
| HTTP 4xx (excepto 429) | Sin reintento; documento a bandeja de revisión con `error_llm` |
| Timeout (>30s) | Reintento x2; luego bandeja revisión |
| `content` no parsea como JSON | Reintento x1 con prompt reforzado; luego bandeja revisión |
| `tipo_documento` o `area` fuera de taxonomía | Post-procesado: mapear a `OTRO` o área default; marcar revisión |
| API key inválida (401) | Sin reintento; alerta al operador vía UI; cola pausada |

## Eventos registrados (auditable)

Por cada llamada se inserta en `eventos_documento`:

```json
{
  "tipo": "llm_llamada",
  "payload": {
    "modelo": "gpt-4o-mini",
    "prompt_hash": "sha256 del prompt completo",
    "tokens_input": 1850,
    "tokens_output": 80,
    "latency_ms": 4231,
    "proveedor": "openai"
  }
}
{
  "tipo": "llm_respuesta",
  "payload": {
    "tipo_documento": "INFORME",
    "area": "GER-DES",
    "confianza": 0.92,
    "justificacion": "..."
  }
}
```

El `prompt_hash` permite detectar respuestas cacheables (mismo prompt →
misma respuesta sin volver a llamar).

## Cache

Antes de cada llamada, el cliente consulta `eventos_documento` por el
`prompt_hash` más reciente con respuesta exitosa para el mismo modelo.
Si existe (y la taxonomía no cambió desde entonces), se reutiliza la
respuesta. Esto reduce costo en migraciones masivas con documentos
repetidos y en reprocesamientos.

## Rate limiting

Token bucket en Redis: clave `llm:ratelimit:{model}`, capacidad =
`LLM_RATE_LIMIT_RPM` (default 50), refill cada minuto. El cliente
adquiere un token antes de cada llamada; si no hay, espera hasta el
próximo refill. Configurable vía `configuracion_llm.rate_limit_rpm`.

## Test de contrato

`backend/tests/contract/test_llm_client.py` usa un mock server
(`pytest-httpserver`) que:

1. Devuelve la respuesta JSON esperada → cliente parsea correctamente.
2. Devuelve 429 → cliente reintenta según backoff.
3. Devuelve JSON malformado → cliente marca error sin crashear.
4. Devuelve `tipo_documento` fuera de taxonomía → post-procesado a
   `OTRO` + revisión.
5. Sin conectividad → cliente encola reintento sin perder el documento.
