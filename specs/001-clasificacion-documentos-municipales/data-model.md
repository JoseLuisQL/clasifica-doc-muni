# Data Model — Clasificación Automática de Documentos Municipales

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07

Modelo de datos PostgreSQL 16. Convenciones: snake_case, timestamps
`TIMESTAMPTZ` con default `now()`, IDs `UUID` (excepto secuencias de
correlativo que usan clave compuesta natural).

## Diagrama ER (texto)

```
usuarios 1───∞ documentos ∞───1 tipos_documentales
                │                 │
                │                 └───∞ areas (via area_tipica)
                │
                ├───∞ eventos_documento
                ├───1 muestras_entrenamiento (opcional)
                └───1 secuencias_correlativo (via area+anio+tipo)

configuracion_llm (singleton)
configuracion_correlativo (singleton)
configuracion_anonimizacion (singleton)
```

## Tablas

### `usuarios`
```sql
CREATE TABLE usuarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,           -- bcrypt
  nombre_completo TEXT NOT NULL,
  rol TEXT NOT NULL DEFAULT 'admin',     -- MVP: solo 'admin'
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `areas`
```sql
CREATE TABLE areas (
  codigo TEXT PRIMARY KEY,               -- ej: 'GER-DES'
  nombre TEXT NOT NULL,                  -- 'Gerencia de Desarrollo Económico'
  padre_codigo TEXT REFERENCES areas(codigo) ON DELETE SET NULL,
  activa BOOLEAN NOT NULL DEFAULT TRUE,
  orden INT NOT NULL DEFAULT 0,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_areas_padre ON areas(padre_codigo);
```

### `tipos_documentales`
```sql
CREATE TABLE tipos_documentales (
  codigo TEXT PRIMARY KEY,               -- ej: 'INF'
  nombre TEXT NOT NULL,                  -- 'Informe'
  area_tipica_codigo TEXT REFERENCES areas(codigo),  -- sugerencia por defecto
  descripcion TEXT,                      -- usada en prompt del LLM
  palabras_clave JSONB NOT NULL DEFAULT '[]',  -- ["informe", "solicito informar", ...]
  plantilla_correlativo TEXT,            -- override del global, ej: '{AREA}-{AÑO}-INF-{SEQ:04d}'
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tipos_activos ON tipos_documentales(activo);
```

### `configuracion_correlativo`
```sql
CREATE TABLE configuracion_correlativo (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- singleton
  plantilla TEXT NOT NULL DEFAULT '{SEQ:04d}-{AREA}-{AÑO}-{TIPO}',  -- secuencia AL INICIO
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> **Nota**: la plantilla por defecto pone la secuencia `SEQ` al inicio
> del correlativo para que los archivos se ordenen naturalmente por
> número de creación. Ej: `0001-GER-DES-2026-INF`. El nombre del
> archivo también incluye un slug del asunto:
> `0001-GDE-2026-INF-informe-solicitud-licencia.pdf` (ver
> `contracts/folder-structure.md`).

### `secuencias_correlativo`
```sql
CREATE TABLE secuencias_correlativo (
  area_codigo TEXT NOT NULL REFERENCES areas(codigo),
  anio INT NOT NULL,
  tipo_codigo TEXT NOT NULL REFERENCES tipos_documentales(codigo),
  ultimo_valor INT NOT NULL DEFAULT 0,
  PRIMARY KEY (area_codigo, anio, tipo_codigo)
);
-- Asignación atómica via SELECT ... FOR UPDATE en esta tabla.
```

### `documentos`
```sql
CREATE TABLE documentos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hash_sha256 TEXT UNIQUE NOT NULL,       -- dedup
  correlativo TEXT,                       -- NULL hasta clasificar
  estado TEXT NOT NULL DEFAULT 'pendiente',
    -- pendiente | procesando | clasificado | revision | error | duplicado
  tipo_codigo TEXT REFERENCES tipos_documentales(codigo),
  area_codigo TEXT REFERENCES areas(codigo),
  asunto TEXT,
  anio_documento INT,
  confianza FLOAT CHECK (confianza BETWEEN 0 AND 1),
  justificacion_llm TEXT,
  ocr_text TEXT,                          -- texto extraído (anonimizado parcial)
  ruta_original TEXT NOT NULL,            -- /data/originales/AB/CD/abcd...pdf
  ruta_clasificada TEXT,                  -- /data/documentos/2026/GER-DES/INF/GER-DES-2026-INF-0001.pdf
  num_paginas INT,
  tamano_bytes BIGINT NOT NULL,
  origen TEXT NOT NULL DEFAULT 'interactivo',  -- interactivo | migracion | watch_folder
  prioridad INT NOT NULL DEFAULT 5,       -- 1 alta (interactivo) ... 10 baja
  operador_id UUID REFERENCES usuarios(id),
  cargado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  procesado_en TIMESTAMPTZ,
  version_config INT NOT NULL DEFAULT 1,  -- snapshot de taxonomía usada
  search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('spanish', coalesce(asunto,'')), 'A') ||
    setweight(to_tsvector('spanish', coalesce(ocr_text,'')), 'B')
  ) STORED
);
CREATE INDEX idx_documentos_estado ON documentos(estado);
CREATE INDEX idx_documentos_correlativo ON documentos(correlativo);
CREATE INDEX idx_documentos_area_tipo_anio ON documentos(area_codigo, tipo_codigo, anio_documento);
CREATE INDEX idx_documentos_cargado_en ON documentos(cargado_en DESC);
CREATE INDEX idx_documentos_search ON documentos USING GIN(search_vector);
CREATE INDEX idx_documentos_asunto_trgm ON documentos USING GIN(asunto gin_trgm_ops);
```

### `eventos_documento`
```sql
CREATE TABLE eventos_documento (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  documento_id UUID NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL,
    -- cargado | ocr_inicio | ocr_fin | anon_inicio | anon_fin |
    -- llm_llamada | llm_respuesta | clasificado | correlativo_asignado |
    -- renombrado | movido | revision | corregido | reintentado | error
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB NOT NULL DEFAULT '{}',
    -- ej llm_llamada: {modelo, prompt_hash, tokens_input, tokens_output, latency_ms}
    -- ej corregido: {campo, valor_anterior, valor_nuevo, operador_id}
    -- ej anon_fin: {patrones: ["DNI:3", "RUC:1", "TEL:2"]}
  CONSTRAINT chk_payload_json CHECK (payload IS NOT NULL)
);
CREATE INDEX idx_eventos_documento_doc ON eventos_documento(documento_id, timestamp DESC);
```

### `muestras_entrenamiento`
```sql
CREATE TABLE muestras_entrenamiento (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  documento_id UUID NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
  tipo_original TEXT,
  area_original TEXT,
  tipo_corregido TEXT NOT NULL,
  area_corregida TEXT NOT NULL,
  operador_id UUID NOT NULL REFERENCES usuarios(id),
  justificacion_operador TEXT,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  usada_en_reentrenamiento BOOLEAN NOT NULL DEFAULT FALSE,
  version_modelo TEXT                       -- versión del prompt/modelo al corregir
);
CREATE INDEX idx_muestras_no_usadas ON muestras_entrenamiento(usada_en_reentrenamiento) WHERE usada_en_reentrenamiento = FALSE;
```

### `configuracion_llm`
```sql
CREATE TABLE configuracion_llm (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  endpoint TEXT NOT NULL DEFAULT 'https://api.openai.com/v1',
  modelo TEXT NOT NULL DEFAULT 'gpt-4o-mini',
  api_key_secret_ref TEXT NOT NULL,        -- referencia a var de entorno, NO el valor
  temperatura FLOAT NOT NULL DEFAULT 0.1,
  max_tokens INT NOT NULL DEFAULT 600,
  rate_limit_rpm INT NOT NULL DEFAULT 50,
  timeout_segundos INT NOT NULL DEFAULT 30,
  plantilla_system_prompt TEXT NOT NULL,
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `configuracion_anonimizacion`
```sql
CREATE TABLE configuracion_anonimizacion (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  patrones JSONB NOT NULL DEFAULT '[
    {"nombre":"DNI","regex":"\\b\\d{8}\\b","contexto":["dni","documento"]},
    {"nombre":"RUC","regex":"\\b\\d{11}\\b"},
    {"nombre":"TEL","regex":"\\b9\\d{8}\\b"},
    {"nombre":"EMAIL","regex":"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"}
  ]',
  redactar_firmas BOOLEAN NOT NULL DEFAULT TRUE,
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `documentos_embeddings` (búsqueda semántica)
```sql
CREATE TABLE documentos_embeddings (
  documento_id UUID PRIMARY KEY REFERENCES documentos(id) ON DELETE CASCADE,
  vector vector(384) NOT NULL,             -- pgvector, paraphrase-multilingual-MiniLM-L12-v2
  modelo TEXT NOT NULL DEFAULT 'paraphrase-multilingual-MiniLM-L12-v2',
  generado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_embeddings_vector ON documentos_embeddings
  USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
-- Para consultas de similitud: ORDER BY vector <=> :query_vec
```

### `jobs_migracion`
```sql
CREATE TABLE jobs_migracion (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ruta_origen TEXT NOT NULL,               -- carpeta migrada
  total_documentos INT NOT NULL DEFAULT 0,
  procesados INT NOT NULL DEFAULT 0,
  exitosos INT NOT NULL DEFAULT 0,
  en_revision INT NOT NULL DEFAULT 0,
  erroneos INT NOT NULL DEFAULT 0,
  estado TEXT NOT NULL DEFAULT 'encolado',  -- encolado | en_curso | pausado | completado | cancelado
  iniciado_en TIMESTAMPTZ,
  finalizado_en TIMESTAMPTZ,
  operador_id UUID NOT NULL REFERENCES usuarios(id)
);
CREATE INDEX idx_jobs_estado ON jobs_migracion(estado);
```

## Extensiones PostgreSQL requeridas

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- búsqueda fuzzy
CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector, búsqueda semántica
```

## Índices adicionales de rendimiento

- `documentos(hash_sha256)` UNIQUE → dedup O(1).
- `documentos(estado, prioridad, cargado_en)` → workers fetch siguiente.
- `eventos_documento(documento_id, timestamp DESC)` → histórico eficiente.

## Política de retención / purga

- `eventos_documento.payload` puede crecer; política de archivo a
  almacenamiento frío tras 1 año (configurable en Fase 3).
- `/data/tmp/ocr/` se purga tras 7 días (cron en `infra/scripts/`).
- `/data/originales/` es inmutable: nunca se borra (salvo orden legal).
