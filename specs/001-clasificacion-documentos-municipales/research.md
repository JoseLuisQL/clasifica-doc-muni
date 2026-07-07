# Research — Clasificación Automática de Documentos Municipales

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07

Investigación de stack y alternativas para cada decisión técnica clave.

## 1. OCR en español para PDFs escaneados

| Opción | Pros | Contras | Decisión |
|--------|------|---------|----------|
| **PaddleOCR** | Excelente en español, detecta orientación, rápido, open-source, soporta layout | Setup pesado (dependencias PaddlePaddle) | ✅ **Primario** |
| Tesseract 5 (vía `pytesseract`) | Ubicuo, simple, sin dependencias pesadas | Peor precisión en español, no maneja layout complejo | Fallback |
| **pdfplumber** (texto nativo) | Extrae texto directamente de PDFs digitales | No hace OCR (solo si el PDF ya tiene texto) | ✅ **Detección previa** |
| Cloud OCR (Textract, Document AI) | Excelente precisión | Sale del perímetro on-premise, costo por doc | ❌ Rechazado por soberanía |

**Decisión**: Pipeline `preprocess.py` detecta con `pdfplumber` si hay
texto extraíble. Si no, usa **PaddleOCR** (español). Si la confianza del
OCR es baja, reintenta con preprocesamiento (deskew con OpenCV,
binarización Otsu, upscale 2x). Tesseract queda como fallback si PaddleOCR
falla al instalar en el servidor.

### Preprocesamiento

- `deskew`: detectar ángulo con Hough transform (OpenCV) y rotar.
- `binarize`: Otsu o adaptive threshold para escaneos con ruido.
- `upscale`: 2x con LANCZOS para DPI bajo.
- `denoise`: fastNlMeansDenoising si el escaneo es granulado.

## 2. LLM multimodal vía API OpenAI-compatible

### Proveedor concreto: Qware

Verificado 2026-07-07:

- **Endpoint**: `https://api.qware.me/v1` (compatible OpenAI).
- **Modelo de clasificación**: `gemini-3-flash-agent` (multimodal,
  soporta `messages` con `image_url`).
- **Auth**: `Authorization: Bearer <LLM_API_KEY>`. La key se gestiona
  como **secret** en variable de entorno, nunca en código ni en el repo.
- **Embeddings**: Qware **NO** expone `/v1/embeddings` (HTTP 404
  verificado). Por ello los embeddings se generan localmente (sección 11).
- **Otros modelos disponibles** (para futuro): `gemini-3.1-flash-image`,
  `gemini-pro-agent`, `gemini-3.1-pro-low`, `gpt-oss-120b-medium`,
  `claude-sonnet-4-6`, `gemini-3.5-flash-low`, `gemini-3.1-flash-lite`.
- **Salida observada**: respuesta con `usage` que incluye
  `reasoning_tokens` (el modelo hace reasoning interno); `temperature`
  y `response_format` respetados.

### Contrato de llamada

- Endpoint: `POST /v1/chat/completions` (estándar OpenAI).
- Modelo configurable (ej: `gpt-4o-mini`, `gpt-4o`, `claude-3-5-sonnet`
  vía proxy, `qwen2-vl-72b` vía proveedor, etc.).
- Mensajes: `system` (rol + taxonomía vigente + formato JSON exigido) +
  `user` (texto OCR truncado a ~6k tokens + 1 imagen primera página en
  base64 o URL `data:`).
- `response_format: { type: "json_schema", json_schema: {...} }` si el
  proveedor lo soporta (fuerza JSON válido).
- `temperature: 0.1` (determinismo).
- `max_tokens: 600`.

### Schema JSON de respuesta (contrato)

```json
{
  "tipo_documento": "INFORME | MEMORANDO | OFICIO | CARTA | RESOLUCION | ORDENANZA | DECRETO | TUPA | ACTA | DENUNCIA",
  "area": "GER-DES | GER-INF | GER-MAM | ...",
  "asunto": "string corto, máx 200 chars",
  "anio_documento": 2026,
  "confianza": 0.0-1.0,
  "justificacion": "string, por qué se eligió el tipo"
}
```

### Manejo de errores y costos

- **Timeout**: 30s por llamada. Si excede, reintento x2 con backoff.
- **Rate limiting**: token bucket en Redis, configurable (ej. 50 req/min).
  Para migraciones masivas, batch de N documentos con throughput cap.
- **Cache**: hash del prompt (texto OCR + taxonomía) → respuesta. Si el
  mismo contenido se reprocesa, se reutiliza la respuesta cacheada.
- **Retry**: errores 5xx y timeout → reintento. Errores 4xx (bad request,
  content policy) → marcar documento para revisión sin reintento.

### Anonimización previa (crítico para soberanía)

Antes de enviar texto OCR + imagen al LLM:

- **DNI**: regex `\b\d{8}\b` (con contexto: palabras "DNI", "Documento"
  cerca) → reemplazar por `[DNI]`.
- **RUC**: regex `\b\d{11}\b` → `[RUC]`.
- **Teléfonos**: `\b9\d{8}\b` (celulares peruanas) → `[TEL]`.
- **Emails**: regex estándar → `[EMAIL]`.
- **Firmas**: en la imagen, detectar regiones inferiores (último 20%
  del documento) con alta densidad de trazos → máscara negra sobre esa
  región antes de enviar al LLM.
- **Log**: `eventos_documento` payload registra qué patrones se
  anonimizaron (no el contenido original). Reversible solo para admin
  con acceso al original.

## 3. Asignación atómica de correlativo

Esquema: `AREA-AÑO-TIPO-NNNN` (configurable). Ej: `GER-DES-2026-INF-0001`.

### Implementación

```sql
-- Tabla de secuencias por (area, año, tipo)
CREATE TABLE secuencias_correlativo (
  area_codigo TEXT NOT NULL,
  anio INT NOT NULL,
  tipo_codigo TEXT NOT NULL,
  ultimo_valor INT NOT NULL DEFAULT 0,
  PRIMARY KEY (area_codigo, anio, tipo_codigo)
);

-- Asignación atómica (Python/SQLAlchemy):
BEGIN;
SELECT ultimo_valor FROM secuencias_correlativo
  WHERE area_codigo=:a AND anio=:y AND tipo_codigo=:t
  FOR UPDATE;
-- si no existe → INSERT con ultimo_valor=1
-- si existe → UPDATE ... SET ultimo_valor = ultimo_valor + 1
COMMIT;
-- correlativo = f"{area}-{anio}-{tipo}-{ultimo_valor:04d}"
```

`FOR UPDATE` bloquea la fila hasta el commit → cero colisiones bajo
concurrencia. Validado con test de stress (10 workers simultáneos, 1000
correlativos por worker,assert sin duplicados).

### Reinicio anual

Las secuencias están particionadas por `año` (PK compuesta). Al cambiar
de año, la primera clasificación de un (area, tipo) inserta una nueva
fila con `ultimo_valor=1`. No requiere job de reinicio.

### Plantilla configurable

`ConfiguracionCorrelativo` permite cambiar el formato (ej:
`{AREA}/{AÑO}/{TIPO}/{SEQ:04d}`, o con prefijo municipal
`MUNI-LURIN-{AREA}-{AÑO}-{TIPO}-{SEQ:05d}`). Render con `str.format`.

## 4. Búsqueda full-text en español

PostgreSQL 16 con:

- `tsvector` generado sobre `documento.ocr_text` + `documento.asunto`.
- Config `spanish` (stemming en español).
- Índice `GIN` sobre el tsvector.
- Trigramas (`pg_trgm`) para búsqueda fuzzy por correlativo/asunto.

```sql
ALTER TABLE documentos ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('spanish', coalesce(asunto,'')), 'A') ||
    setweight(to_tsvector('spanish', coalesce(ocr_text,'')), 'B')
  ) STORED;
CREATE INDEX idx_documentos_search ON documentos USING GIN(search_vector);
```

Consulta: `ts_rank_cd` + `ts_headline` para snippets. Filtros adicionales
por `area`, `tipo`, `anio`, `confianza`, `fecha_carga` con índices B-tree.

## 5. Pipeline de colas (Celery)

- **Broker + backend**: Redis.
- **Colas**:
  - `interactive` (prioridad alta, prefetch=1): uploads individuales.
  - `batch` (prioridad media, prefetch configurable): migraciones.
  - `retry` (prioridad baja): reintentos programados.
- **Workers**: contenedores separados, escalables horizontalmente.
- **Idempotencia**: cada tarea tiene `task_id = document_id`; Celery
  deduplica si la misma tarea se encola dos veces.
- **Progreso en vivo**: WebSocket del frontend suscrito a canal Redis
  `document:{id}:events`; workers publican eventos allí.

## 6. Frontend: stack

- **React 18 + Vite**: build rápido, ecosystem maduro.
- **TanStack Query**: caching, polling, optimistic updates.
- **TanStack Router**: routing type-safe (alternativa a React Router).
- **Zustand**: estado global ligero (auth, sesión migración).
- **Tailwind + shadcn/ui**: UI consistente, accesible, dark mode.
- **react-dropzone**: drag&drop con validación (PDF, tamaño máx 50MB).
- **react-pdf**: preview del PDF en el detalle y bandeja de revisión.

## 7. Seguridad on-premise

- **Auth**: JWT (access 15min + refresh 7d), bcrypt para password.
  Usuario único MVP, pero tablas con `usuario_id` para RBAC futuro.
- **API key del LLM**: en variable de entorno / Docker secret. Nunca en
  código ni logs. El `LLMClient` la lee de settings.
- **HTTPS**: Nginx con cert autofirmado (o Let's Encrypt si hay dominio).
- **CORS**: solo el frontend origin en prod.
- **Rate limiting**: API + LLM client.
- **Auditoría**: tabla `eventos_documento` + log estructurado a archivo
  rotativo (JSON lines) en `/var/log/clasifica/`.

## 8. Despliegue on-premise

- **Docker Compose**: un comando `docker compose up -d` levanta todo.
- **Volúmenes**: `data/`, `db/`, `redis/` montados en host.
- **Backups**: cron con `pg_dump` + rsync de `/data/documentos/` a disco
  externo. Script en `infra/scripts/backup.sh`.
- **Updates**: `docker compose pull && docker compose up -d`. Migraciones
  Alembic auto-ejecutadas en entrypoint del backend.
- **Monitoreo**: `/health` endpoint + logs estructurados. Sin Prometheus
  en MVP (complejidad), pero hooks para añadirlo después.

## 9. Dataset de prueba y métricas

- `tests/fixtures/pdfs/`: ~50 PDFs sintéticos + muestras anonimizadas
  aportadas por la municipalidad, versionados con DVC (no en git por
  peso/privacidad).
- `tests/fixtures/expected_classifications.json`: ground truth.
- Script `scripts/eval_classifier.py` corre clasificación sobre el set y
  reporta: precisión por tipo, por área, matriz de confusión, tiempo p50/p95.
- Métrica objetivo: ≥90% precisión (tipo+área) en primera pasada (SC-001).

## 10. Decisiones diferidas (fases futuras)

- **Retención legal por tipo** (NQ-002 resuelto: ninguna por ahora):
  tabla `politicas_retencion` diferida a Fase 3, con job de
  archivo/purga controlado por admin. MVP conserva indefinidamente.
- **Firma digital** (NQ-003 resuelto: NO): fuera de alcance MVP.
- **Reentrenamiento** (Fase 5): las muestras de `MuestraEntrenamiento`
  alimentan un few-shot prompt dinámico o un fine-tune del modelo base.

## 11. Búsqueda semántica con embeddings locales

El proveedor Qware no expone `/v1/embeddings` (404 verificado). Para la
búsqueda "inteligente" por concepto (no solo keyword), se usan
**embeddings locales** on-premise — lo que además refuerza la
soberanía de datos: el OCR completo del documento no sale al proveedor
LLM para generar embeddings.

### Modelo de embeddings

| Opción | Dim | Tamaño | Español | Decisión |
|--------|-----|--------|---------|----------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | ~120MB | Bueno | ✅ **Default** (rápido, ligero) |
| `intfloat/multilingual-e5-small` | 384 | ~470MB | Muy bueno | Alternativa si se necesita más calidad |
| `intfloat/multilingual-e5-base` | 768 | ~2.2GB | Excelente | Solo si hay RAM sobrante y se prioriza calidad |
| BGE-m3 | 1024 | ~2.3GB | Excelente + multilingüe | Fase futura (mejor pero pesado) |

**Decisión**: `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, 120MB).
Corre en CPU (~50ms por documento en CPU moderno). Se carga una sola vez
al arranque del worker y se mantiene en memoria. Configurable vía
`configuracion_llm.modelo_embeddings`.

### Almacenamiento: pgvector

- Extensión `pgvector` en PostgreSQL 16.
- Tabla `documentos_embeddings` con columna `vector vector(384)`.
- Índice `ivfflat` (HNSW si PG17+): `CREATE INDEX ... USING ivfflat
  (vector vector_cosine_ops)`.
- Consulta de similitud:
  `SELECT id, 1 - (vector <=> :query_vec) AS sim FROM documentos_embeddings
   ORDER BY vector <=> :query_vec LIMIT 20`.

### Pipeline de embedding

1. Tras clasificar un documento, el worker genera el embedding de
   `asunto + "\n" + ocr_text[:4000]` (truncado para controlar costo CPU).
2. Inserta en `documentos_embeddings`.
3. Si el operador corrige el asunto, se regenera el embedding.

### Búsqueda híbrida (inteligente)

El endpoint `/documents/search` combina:

- **Full-text** (tsvector español + trigramas): score A = `ts_rank_cd`.
- **Semántica** (pgvector): score B = `1 - cosine_distance`.
- **Filtros facetados**: área, tipo, año, rango fechas, confianza,
  estado, origen — aplicados como WHERE.
- **Score híbrido**: `final = α·normalize(A) + (1-α)·B`, α configurable
  (default 0.5). El usuario puede elegir modo "exacto" (α=1),
  "semántico" (α=0) o "híbrido" (default) en la UI.

### Documentos similares

Endpoint `/documents/{id}/similar`: genera o recupera el embedding del
documento y consulta top-K por similitud coseno. Útil para agrupar
documentos relacionados (ej. todos los oficios sobre el mismo trámite).

### Autocompletado

- `/search/suggest?q=...`: busca prefijos en `asunto` (índice trgm) +
  códigos de área/tipo. Retorna top-10 sugerencias.
