# Implementation Plan: Clasificación Automática de Documentos Municipales

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07
| **Spec**: [spec.md](./spec.md)

## Summary

Sistema on-premise para clasificar PDFs escaneados de municipalidades
distritales del Perú. Pipeline: upload → OCR (español) → anonimización
PII → LLM multimodal (Qware `gemini-3-flash-agent`, API OpenAI-compatible)
para clasificar tipo/área/asunto/año → asignación atómica de correlativo
`NNNN-AREA-AÑO-TIPO` (secuencia al inicio) → renombrado + ubicación física
en `/AÑO/AREA/TIPO/NNNN-AREA-AÑO-TIPO-ASUNTO.pdf` → indexación full-text
**+ embeddings semánticos locales** (sentence-transformers + pgvector) →
UI de revisión y exploración con búsqueda inteligente (keyword +
semántica + facetada). Soporta carga individual (interactiva, ≤15s) y
masiva (migración histórica vía colas). Stack: Python 3.12 + FastAPI +
Celery + PostgreSQL 16 (pgvector) + Redis + React + Vite. Catálogo TUPA
base precargado (~40 áreas, ~50 tipos) según Ley 27972.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)

**Primary Dependencies**:
- Backend: FastAPI, Celery, SQLAlchemy 2.0 (async), Alembic, Pydantic v2,
  pdfplumber, pytesseract / PaddleOCR, Pillow, httpx (LLM client),
  sentence-transformers (embeddings locales), pgvector (PG),
  python-multipart, python-jose (JWT), passlib[bcrypt]
- Frontend: React 18, Vite, TanStack Query, TanStack Router, Zustand,
  Tailwind CSS, shadcn/ui, react-dropzone, react-pdf
- Infra: PostgreSQL 16 (con `pg_trgm` + `tsvector` + extensión `pgvector`),
  Redis 7, Nginx (reverse proxy), Docker Compose

**Storage**:
- PostgreSQL 16: metadatos, eventos, configuración, muestras, secuencias.
- Filesystem (montaje local): `/data/documentos/{AÑO}/{AREA}/{TIPO}/`,
  `/data/originales/`, `/data/tmp/ocr/`.
- Redis: colas Celery + cache de sesiones + rate limiting LLM.

**Testing**: pytest + pytest-asyncio + pytest-cov (backend, ≥80%),
Vitest + Playwright (frontend), testcontainers para integración PG/Redis.

**Target Platform**: Linux x86_64 (Ubuntu 22.04+), on-premise, Docker.

**Project Type**: web-service (backend API + SPA frontend + workers).

**Performance Goals**:
- Carga individual p95 ≤15s (OCR ~3-5s + LLM ~3-8s + organización ~1s).
- Migración 1000 docs en ≤4h (16 workers, ~240 docs/hora).
- Búsqueda full-text ≤2s sobre 100k docs.

**Constraints**:
- Sin GPU local (LLM externo).
- Operación offline para consulta/organización; solo LLM requiere red.
- Memoria servidor: 16GB min, 32GB recomendado.
- Ancho de banda salida limitado para migraciones (rate limit configurable).

**Scale/Scope**: MVP mono-municipalidad, usuario único, ~100k documentos
capacidad inicial; arquitectura preparada para multi-tenant futuro.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Notas |
|-----------|--------|-------|
| I. Soberanía de datos local | ✅ | PDFs + BD locales; solo contenido anonimizado al LLM |
| II. Clasificación determinista y explicable | ✅ | Tabla `eventos_documento` registra prompt+respuesta+modelo; correlativo por reglas |
| III. Idempotencia y trazabilidad | ✅ | Dedup por SHA-256; `/originales/` inmutable; log de eventos |
| IV. Tiempo real + lote misma tubería | ✅ | Celery unificado con prioridades |
| V. Configuración sobre código | ✅ | Tipos/áreas/prompts en tablas + YAML |
| VI. Test-first | ✅ | pytest ≥80%, fixtures con DVC |
| VII. Simple y operable | ✅ | UI cubre todo el flujo; CLI solo para migración/mantenimiento |

## Project Structure

### Documentation (this feature)

```text
specs/001-clasificacion-documentos-municipales/
├── plan.md              # Este archivo
├── research.md          # Investigación de stack y alternativas
├── data-model.md        # Modelo de datos (entidades, relaciones, índices)
├── quickstart.md        # Cómo levantar el sistema en 10 min
├── contracts/
│   ├── api-spec.yaml    # OpenAPI 3.1 del backend
│   ├── llm-contract.md  # Contrato del prompt/respuesta LLM
│   └── folder-structure.md  # Contrato de carpetas físicas
└── tasks.md             # Generado por /speckit.tasks (pendiente)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── alembic/                  # Migraciones DB
├── src/clasifica/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory
│   ├── config.py             # Settings (pydantic-settings, vars de entorno)
│   ├── db/
│   │   ├── base.py           # Async engine, session factory
│   │   └── models/           # SQLAlchemy models (documento, evento, tipo, area, ...)
│   ├── api/
│   │   ├── deps.py           # Auth, paginación, sesión
│   │   └── routes/           # documents, uploads, classification, config, search, exports
│   ├── schemas/              # Pydantic DTOs
│   ├── services/
│   │   ├── ocr.py            # OCR pipeline (nativo vs escaneado)
│   │   ├── preprocess.py     # deskew, binarize, upscale
│   │   ├── anonymize.py      # PII redaction (DNI, RUC, firmas)
│   │   ├── llm_client.py     # OpenAI-compatible client
│   │   ├── classifier.py     # Orquesta OCR→anon→LLM→postprocesado
│   │   ├── correlativo.py    # Asignación atómica AREA-AÑO-TIPO-SEQ
│   │   ├── organizer.py      # Renombrado + ubicación física
│   │   ├── dedup.py          # SHA-256 check
│   │   ├── search.py         # Full-text + filtros
│   │   └── exporter.py       # ZIP + CSV + reportes
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks/            # process_document, batch_migration, retry
│   ├── core/
│   │   ├── security.py       # JWT, hashing
│   │   ├── logging.py        # Structured logging
│   │   └── errors.py
│   └── cli/                  # CLI para migraciones masivas / mantenimiento
├── tests/
│   ├── unit/
│   ├── integration/          # testcontainers PG/Redis
│   ├── contract/             # API contract tests
│   └── fixtures/             # PDFs de prueba (DVC)
└── Dockerfile

frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── router.tsx            # TanStack Router
│   ├── api/                  # Cliente API generado desde OpenAPI
│   ├── stores/               # Zustand
│   ├── components/ui/        # shadcn/ui
│   ├── features/
│   │   ├── auth/
│   │   ├── upload/           # Carga individual + drag&drop
│   │   ├── migration/        # Carga masiva + progreso
│   │   ├── review/           # Bandeja de revisión
│   │   ├── explorer/         # Navegación árbol + búsqueda
│   │   ├── document/         # Detalle + eventos + preview
│   │   └── config/           # Taxonomía + prompts + anon
│   └── lib/
├── tests/                    # Vitest + Playwright
└── Dockerfile

infra/
├── docker-compose.yml        # backend, worker, frontend, db, redis, nginx
├── docker-compose.prod.yml
└── nginx/clasifica.conf

data/                         # Montaje de datos (gitignored)
├── originales/               # Inmutable, por hash
├── documentos/{AÑO}/{AREA}/{TIPO}/
└── tmp/
```

**Structure Decision**: Web application (backend + frontend) con workers
Celery separados del proceso API. Un solo repo monorepo. `infra/` contiene
el despliegue Docker Compose on-premise. La separación API/worker permite
escalar workers independientes para migraciones masivas sin tocar la API.

## Architecture Overview

### Pipeline de procesamiento (unificado interactivo + masivo)

```
[Upload UI / Watch-folder CLI]
        │
        ▼
[API: POST /documents] ──► hash SHA-256 ──► dedup check
        │                                      │
        │                                 (exists?) ──► link + return existing
        │
        ▼
[Cola Celery: process_document]  (prioridad: interactive > batch)
        │
        ├── 1. Persistir Documento (estado=pendiente) + Evento "cargado"
        ├── 2. Detectar texto nativo (pdfplumber)
        │      ├─ tiene texto → usar directo
        │      └─ no → OCR (PaddleOCR/tesseract, español) + preprocess si baja calidad
        ├── 3. Anonimizar PII (regex DNI \d{8}, RUC \d{11}, emails, teléfonos)
        │      + redact regiones de firma (inferencia por layout)
        ├── 4. LLM multimodal (httpx → API OpenAI-compatible)
        │      input: texto OCR (truncado) + imagen primera página
        │      output JSON: {tipo, area, asunto, año, confianza, justificacion}
        │      taxonomía vigente inyectada en system prompt
        ├── 5. Post-procesado:
        │      - validar tipo/area contra taxonomía configurada
        │      - si confianza < 0.70 → estado=revisión
        │      - si confianza ≥ 0.70 → estado=clasificado
        ├── 6. Asignación correlativo (SELECT FOR UPDATE en SecuenciaCorrelativo)
        ├── 7. Renombrar + ubicar físico (hardlink desde /originales/)
        ├── 8. Indexar full-text (tsvector sobre OCR + asunto)
        └── 9. Evento "clasificado" + (si revisión) "marcado para revisión"
        │
        ▼
[WS push al frontend / polling] ──► actualización en vivo
```

### Componentes clave

- **API FastAPI**: endpoints REST + WebSocket para progreso en vivo.
- **Workers Celery**: `process_document` (interactivo, prioridad alta),
  `batch_migration` (orquesta carpetas), `retry_failed`. Concurrencia
  configurable (prefetch=1, max workers=N).
- **LLM Client**: abstracción `LLMClient` con retries/backoff, timeout,
  rate limiting (token bucket en Redis), fallback a cola si API cae.
  Implementa contrato `llm-contract.md`. Proveedor concreto: **Qware**
  (`https://api.qware.me/v1`, modelo `gemini-3-flash-agent`).
- **Embeddings locales**: `EmbeddingService` con `sentence-transformers`
  (modelo `paraphrase-multilingual-MiniLM-L12-v2`, ~120MB, multilingüe
  con buen español). Genera embedding 384-dim del `asunto + ocr_text`
  (truncado). Almacenado en `documentos_embeddings` (pgvector). NO
  depende del proveedor LLM — corre 100% on-premise en CPU. Refuerza
  soberanía de datos (el OCR completo nunca sale para embeddings).
- **Buscador inteligente**: combina (a) full-text PostgreSQL (tsvector
  español + trigramas) para keyword exacto, (b) similitud coseno sobre
  pgvector para semántica por concepto, (c) filtros facetados, (d)
  autocompletado. Score híbrido ponderado.
- **Anonimizador**: regex + heurísticas de layout. Log de qué se
  anonimizó por documento (auditable, reversible solo por admin).
- **Asignador de correlativo**: transacción `SELECT ... FOR UPDATE` en
  `secuencias_correlativo(area, año, tipo)`, garantiza cero colisiones
  bajo concurrencia.
- **Organizador de archivos**: hardlink (no copia) desde `/originales/`
  para ahorrar espacio; fallback a copia si filesystem no soporta hardlink
  cross-device.

## Complexity Tracking

> No hay violaciones de constitución que justificar. Tabla vacía.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Risks & Mitigations

| Riesgo | Prob | Impacto | Mitigación |
|--------|------|---------|-----------|
| API LLM caída a mitad de migración | Media | Alto | Cola persistente + retry backoff; documentos quedan "esperando LLM" |
| Costo LLM en migraciones masivas | Alta | Medio | Rate limit configurable; batching; cache de respuestas por hash de prompt |
| Precisión OCR en escaneos malos | Media | Alto | Preprocesamiento + reintento; bandeja de revisión |
| Fuga de PII al LLM externo | Baja | Crítico | Anonimización previa + log auditable + opt-out por documento |
| Colisión de correlativo | Baja | Alto | `SELECT FOR UPDATE` + test de concurrencia |
| Disco lleno por hardlinks | Media | Medio | Monitoring + alerta; política de purga de `/tmp` |
| Modelo LLM deprecado por proveedor | Media | Medio | Abstracción `LLMClient` permite cambiar modelo vía config |

## Phases (roadmap de features)

- **Fase 1 (MVP, esta spec)**: P1+P2+P3 — carga individual, masiva,
  revisión. Usuario único, una municipalidad.
- **Fase 2**: P4+P5 — exploración/búsqueda/exportación + configuración
  UI. Reportes.
- **Fase 3**: RBAC multi-usuario + áreas con permisos + auditoría.
- **Fase 4**: Integraciones (API mesa de partes, SISGEDO), firma digital.
- **Fase 5**: Reentrenamiento con muestras humanas (fine-tuning o RAG
  few-shot con correcciones pasadas).

Este plan cubre Fase 1 (MVP). Las fases siguientes se especifican en
features posteriores.
