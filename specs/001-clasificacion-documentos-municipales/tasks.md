---
description: "Task list para la implementación de la clasificación automática de documentos municipales"
---

# Tasks: Clasificación Automática de Documentos Municipales

**Input**: Design documents from `/specs/001-clasificacion-documentos-municipales/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUIDOS. La constitución exige TDD estricto (principio VI,
cobertura ≥80% en `backend/src`). Los tests se escriben ANTES de la
implementación y deben fallar primero.

**Organization**: Tareas agrupadas por user story (US1-US5) para permitir
implementación y prueba independientes. MVP = Setup + Foundational + US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias)
- **[Story]**: A qué user story pertenece (US1-US5, o FOUND/SETUP/POLISH)
- Incluye rutas de archivo exactas

## Path Conventions (web app)

- Backend: `backend/src/clasifica/`, tests en `backend/tests/`
- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Infra: `infra/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialización del monorepo, dependencias y tooling.

- [ ] T001 [SETUP] Crear estructura de directorios del monorepo según plan.md (`backend/`, `frontend/`, `infra/`, `data/`) con `.gitkeep` en carpetas vacías
- [ ] T002 [SETUP] Inicializar backend: `backend/pyproject.toml` (Python 3.12) con FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Celery, httpx, pdfplumber, paddleocr, pillow, sentence-transformers, pgvector, python-jose, passlib[bcrypt], python-multipart
- [ ] T003 [P] [SETUP] Inicializar frontend: `frontend/package.json` (Vite + React 18 + TS) con TanStack Query/Router, Zustand, Tailwind, shadcn/ui, react-dropzone, react-pdf
- [ ] T004 [P] [SETUP] Configurar linting/formatting backend: `ruff` + `mypy` en `backend/pyproject.toml`, pre-commit hook
- [ ] T005 [P] [SETUP] Configurar linting/formatting frontend: ESLint + Prettier + `tsconfig.json`
- [ ] T006 [P] [SETUP] Configurar pytest en `backend/pyproject.toml` (pytest-asyncio, pytest-cov ≥80%, testcontainers) y estructura `backend/tests/{unit,integration,contract,fixtures}/`
- [ ] T007 [P] [SETUP] Configurar Vitest + Playwright en `frontend/` y estructura `frontend/tests/`
- [ ] T008 [SETUP] Crear `infra/docker-compose.yml` (servicios: backend, worker, frontend, db=postgres16+pgvector, redis, nginx) y `infra/docker-compose.prod.yml`
- [ ] T009 [P] [SETUP] Crear `backend/Dockerfile` y `frontend/Dockerfile` multi-stage
- [ ] T010 [P] [SETUP] Crear `infra/nginx/clasifica.conf` (reverse proxy, CORS, HTTPS autofirmado)
- [ ] T011 [P] [SETUP] Crear `infra/scripts/backup.sh` (pg_dump + rsync de /data) y `infra/scripts/purge_tmp.sh` (purga /tmp/ocr 7 días)

**Checkpoint**: Monorepo levanta con `docker compose up` (servicios vacíos OK).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura core que DEBE estar completa antes de CUALQUIER
user story. Incluye BD, config, auth, LLM client, OCR, embeddings, colas.

**⚠️ CRITICAL**: Ninguna user story puede empezar hasta completar esta fase.

### Configuración y base

- [ ] T012 [FOUND] Implementar `backend/src/clasifica/config.py` (pydantic-settings leyendo `.env`: LLM_*, EMBEDDING_*, POSTGRES_*, REDIS_*, SECRET_KEY, DATA_DIR, ADMIN_*)
- [ ] T013 [FOUND] Implementar `backend/src/clasifica/db/base.py` (async engine, session factory, Base declarativa)
- [ ] T014 [FOUND] Configurar Alembic en `backend/alembic/` (env.py async, migración inicial con extensiones `pg_trgm`, `pgcrypto`, `vector`)
- [ ] T015 [FOUND] Implementar `backend/src/clasifica/core/logging.py` (structured logging JSON a `/var/log/clasifica/`) y `core/errors.py` (jerarquía de excepciones)

### Modelos de datos (data-model.md) — todos [P], archivos distintos

- [ ] T016 [P] [FOUND] Modelo `Usuario` en `backend/src/clasifica/db/models/usuario.py`
- [ ] T017 [P] [FOUND] Modelo `Area` en `backend/src/clasifica/db/models/area.py`
- [ ] T018 [P] [FOUND] Modelo `TipoDocumental` en `backend/src/clasifica/db/models/tipo_documental.py`
- [ ] T019 [P] [FOUND] Modelo `Documento` (con `search_vector` generado) en `backend/src/clasifica/db/models/documento.py`
- [ ] T020 [P] [FOUND] Modelo `EventoDocumento` en `backend/src/clasifica/db/models/evento.py`
- [ ] T021 [P] [FOUND] Modelo `SecuenciaCorrelativo` en `backend/src/clasifica/db/models/secuencia.py`
- [ ] T022 [P] [FOUND] Modelo `MuestraEntrenamiento` en `backend/src/clasifica/db/models/muestra.py`
- [ ] T023 [P] [FOUND] Modelos singleton `ConfiguracionLLM`, `ConfiguracionCorrelativo`, `ConfiguracionAnonimizacion` en `backend/src/clasifica/db/models/configuracion.py`
- [ ] T024 [P] [FOUND] Modelo `JobMigracion` en `backend/src/clasifica/db/models/job_migracion.py`
- [ ] T025 [P] [FOUND] Modelo `DocumentoEmbedding` (pgvector `vector(384)`) en `backend/src/clasifica/db/models/embedding.py`
- [ ] T026 [FOUND] Generar migración Alembic con todas las tablas + índices (GIN search_vector, trgm asunto, ivfflat embeddings, área+tipo+año) (depende T016-T025)

### Seed del catálogo TUPA

- [ ] T027 [FOUND] Crear `backend/src/clasifica/db/seeds/tupa_base.yaml` con las ~40 áreas y ~50 tipos de `contracts/tupa-catalogo.md`
- [ ] T028 [FOUND] Implementar seeder `backend/src/clasifica/db/seeds/loader.py` (carga tupa_base.yaml + configuraciones singleton default + usuario admin desde `.env`)

### Servicios core (pipeline)

- [ ] T029 [P] [FOUND] Test unitario de `dedup` (SHA-256) en `backend/tests/unit/test_dedup.py` (debe fallar)
- [ ] T030 [FOUND] Implementar `backend/src/clasifica/services/dedup.py` (hash SHA-256, check existencia) — pasa T029
- [ ] T031 [P] [FOUND] Test contract del cliente LLM en `backend/tests/contract/test_llm_client.py` (mock httpserver: respuesta JSON válida, 429 backoff, JSON malformado, tipo fuera de taxonomía, sin conectividad) según `contracts/llm-contract.md` (debe fallar)
- [ ] T032 [FOUND] Implementar `backend/src/clasifica/services/llm_client.py` (httpx a Qware, response_format json_schema, retries/backoff, rate limit token-bucket Redis, cache por prompt_hash, timeout) — pasa T031
- [ ] T033 [P] [FOUND] Test unitario de anonimización en `backend/tests/unit/test_anonymize.py` (DNI, RUC, teléfono, email, log de patrones) (debe fallar)
- [ ] T034 [FOUND] Implementar `backend/src/clasifica/services/anonymize.py` (regex configurable + redacción de firmas en imagen) — pasa T033
- [ ] T035 [P] [FOUND] Test unitario OCR/preprocess en `backend/tests/unit/test_ocr.py` (detección texto nativo vs escaneado, deskew/binarize) (debe fallar)
- [ ] T036 [FOUND] Implementar `backend/src/clasifica/services/preprocess.py` (deskew, binarize, upscale con OpenCV) y `services/ocr.py` (pdfplumber nativo + PaddleOCR español + reintento) — pasa T035
- [ ] T037 [P] [FOUND] Test unitario de embeddings en `backend/tests/unit/test_embeddings.py` (genera vector 384-dim, similitud coseno) (debe fallar)
- [ ] T038 [FOUND] Implementar `backend/src/clasifica/services/embeddings.py` (sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2`, carga singleton, embed de asunto+ocr) — pasa T037
- [ ] T039 [P] [FOUND] Test unitario de correlativo concurrente en `backend/tests/integration/test_correlativo.py` (10 workers, sin colisión, SELECT FOR UPDATE, plantilla SEQ-first) (debe fallar)
- [ ] T040 [FOUND] Implementar `backend/src/clasifica/services/correlativo.py` (asignación atómica `SELECT FOR UPDATE`, render plantilla `{SEQ:04d}-{AREA}-{AÑO}-{TIPO}`) — pasa T039
- [ ] T041 [P] [FOUND] Test contract de estructura de carpetas en `backend/tests/contract/test_folder_structure.py` según `contracts/folder-structure.md` (debe fallar)
- [ ] T042 [FOUND] Implementar `backend/src/clasifica/services/organizer.py` (guardar original por hash sharded, hardlink a `/AÑO/AREA/TIPO/CORRELATIVO-slug.pdf`, slug de asunto) — pasa T041

### Orquestación, auth y colas

- [ ] T043 [FOUND] Implementar `backend/src/clasifica/services/classifier.py` (orquesta: ocr→anon→llm→postprocesado→validar taxonomía→umbral confianza 0.70) usando servicios previos
- [ ] T044 [FOUND] Implementar `backend/src/clasifica/core/security.py` (JWT access/refresh, bcrypt) y `api/deps.py` (auth dep, paginación, sesión DB)
- [ ] T045 [FOUND] Implementar `backend/src/clasifica/workers/celery_app.py` (broker Redis, colas `interactive`/`batch`/`retry`, prioridades, prefetch=1)
- [ ] T046 [FOUND] Implementar tarea `backend/src/clasifica/workers/tasks/process_document.py` (pipeline completo: dedup→persistir→ocr→anon→llm→correlativo→organizar→embedding→eventos; publica progreso a canal Redis)
- [ ] T047 [FOUND] Implementar `backend/src/clasifica/main.py` (FastAPI app factory, montaje routers, WebSocket `/ws/documents/{id}`, healthcheck `/health`, CORS)
- [ ] T048 [FOUND] Implementar entrypoint `backend/docker-entrypoint.sh` (alembic upgrade + seed + arranque uvicorn/celery)

**Checkpoint**: Foundation lista. `docker compose up` levanta BD migrada + seed TUPA + admin. El pipeline `process_document` procesa un PDF de fixture de extremo a extremo (verificable con test de integración). Las user stories pueden empezar.

---

## Phase 3: User Story 1 - Carga individual con clasificación en tiempo real (Priority: P1) 🎯 MVP

**Goal**: El operador sube un PDF y en ≤15s ve OCR + clasificación (tipo,
área, asunto, año, confianza) + correlativo propuesto; confirma/corrige;
el archivo se renombra, ubica e indexa.

**Independent Test**: Subir un PDF de informe de fixture y verificar que
se clasifica, renombra a `0001-GDE-2026-INF-....pdf`, se ubica en
`/2026/GDE/INF/` y aparece con todos los metadatos.

### Tests for User Story 1 ⚠️ (escribir primero, deben fallar)

- [ ] T049 [P] [US1] Contract test `POST /auth/login` + `/auth/refresh` en `backend/tests/contract/test_auth.py`
- [ ] T050 [P] [US1] Contract test `POST /documents` (upload) y `GET /documents/{id}` en `backend/tests/contract/test_documents_upload.py`
- [ ] T051 [P] [US1] Contract test `POST /documents/{id}/classify` (corrección manual, recalcula correlativo) en `backend/tests/contract/test_classify.py`
- [ ] T052 [P] [US1] Integration test del flujo completo (upload→clasificado→ubicado→correlativo) en `backend/tests/integration/test_us1_upload_flow.py`

### Implementation for User Story 1

- [ ] T053 [P] [US1] Schemas Pydantic (LoginRequest, TokenPair, Document, ClassifyRequest, UploadRequest) en `backend/src/clasifica/schemas/`
- [ ] T054 [US1] Router `backend/src/clasifica/api/routes/auth.py` (login, refresh) — pasa T049
- [ ] T055 [US1] Router `backend/src/clasifica/api/routes/documents.py` (POST upload → encola en cola `interactive`; GET detalle; GET preview PDF) — pasa T050
- [ ] T056 [US1] Endpoint `POST /documents/{id}/classify` en `documents.py` (corrección manual + reprocesar LLM, recalcula correlativo, reubica, registra evento + muestra) — pasa T051
- [ ] T057 [US1] Endpoint `GET /documents/{id}/events` en `documents.py` (log auditable)
- [ ] T058 [US1] Verificar tarea `process_document` publica eventos por WebSocket para feedback ≤15s — pasa T052
- [ ] T059 [P] [US1] Frontend: feature `auth` (login page, store Zustand, interceptor JWT) en `frontend/src/features/auth/`
- [ ] T060 [P] [US1] Frontend: cliente API generado desde `contracts/api-spec.yaml` en `frontend/src/api/`
- [ ] T061 [US1] Frontend: feature `upload` (drag&drop react-dropzone, preview react-pdf, panel de clasificación editable, WebSocket progreso) en `frontend/src/features/upload/`
- [ ] T062 [US1] Frontend: feature `document` (detalle + eventos + preview) en `frontend/src/features/document/`
- [ ] T063 [P] [US1] E2E Playwright: subir PDF → ver clasificación → corregir → guardar en `frontend/tests/e2e/us1_upload.spec.ts`

**Checkpoint**: US1 funcional e independiente. **Esto es el MVP demo-able.**

---

## Phase 4: User Story 2 - Carga masiva de documentos históricos (Priority: P2)

**Goal**: Migrar cientos de PDFs en lote, procesamiento paralelo, progreso
por documento, bandeja de baja confianza, pausar/reanudar.

**Independent Test**: Apuntar a carpeta con 50 PDFs, ejecutar migración,
verificar que todos quedan clasificados/en revisión/error con reporte final.

### Tests for User Story 2 ⚠️

- [ ] T064 [P] [US2] Contract test `POST /migration/jobs`, `GET`, `pause`, `resume` en `backend/tests/contract/test_migration.py`
- [ ] T065 [P] [US2] Integration test migración de 50 PDFs fixture (paralelo, estados, pausa/reanudar) en `backend/tests/integration/test_us2_migration.py`

### Implementation for User Story 2

- [ ] T066 [P] [US2] Schemas MigrationRequest/MigrationJob en `backend/src/clasifica/schemas/migracion.py`
- [ ] T067 [US2] Tarea `backend/src/clasifica/workers/tasks/batch_migration.py` (recorre carpeta, encola en cola `batch` con prioridad baja, actualiza contadores del job)
- [ ] T068 [US2] Router `backend/src/clasifica/api/routes/migration.py` (crear/listar/estado/pausar/reanudar job) — pasa T064
- [ ] T069 [US2] Implementar CLI `backend/src/clasifica/cli/__init__.py` comando `clasifica migrate <carpeta>` y `clasifica jobs status` — pasa T065
- [ ] T070 [US2] Lógica de pausa/reanudar (flag en `JobMigracion`, workers verifican estado antes de tomar nuevo doc)
- [ ] T071 [P] [US2] Frontend: feature `migration` (selector carpeta/multi-archivo, barra progreso, estado por doc, pausar/reanudar) en `frontend/src/features/migration/`
- [ ] T072 [P] [US2] E2E Playwright migración masiva en `frontend/tests/e2e/us2_migration.spec.ts`

**Checkpoint**: US1 + US2 funcionan independientemente.

---

## Phase 5: User Story 3 - Revisión y corrección de clasificaciones (Priority: P3)

**Goal**: Bandeja de revisión para documentos de baja confianza/conflictos;
edición manual con reubicación y feedback loop para reentrenamiento.

**Independent Test**: Generar 10 docs con clasificación ambigua, verificar
que aparecen en la bandeja, corregir 5, comprobar reubicación + registro.

### Tests for User Story 3 ⚠️

- [ ] T073 [P] [US3] Contract test `GET /documents/review` en `backend/tests/contract/test_review.py`
- [ ] T074 [P] [US3] Integration test bandeja + corrección + reubicación + muestra en `backend/tests/integration/test_us3_review.py`

### Implementation for User Story 3

- [ ] T075 [US3] Endpoint `GET /documents/review` (documentos estado=revision) en `backend/src/clasifica/api/routes/documents.py` — pasa T073
- [ ] T076 [US3] Asegurar que la corrección (T056) registra `MuestraEntrenamiento` con diff original→corregido — pasa T074
- [ ] T077 [P] [US3] Frontend: feature `review` (bandeja, PDF+OCR+sugerencia LLM+justificación, campos editables pre-cargados) en `frontend/src/features/review/`
- [ ] T078 [P] [US3] E2E Playwright bandeja de revisión en `frontend/tests/e2e/us3_review.spec.ts`

**Checkpoint**: US1 + US2 + US3 funcionan independientemente.

---

## Phase 6: User Story 4 - Exploración, búsqueda inteligente y exportación (Priority: P4)

**Goal**: Navegar por año→área→tipo; búsqueda híbrida (asunto, documento,
contenido) con modos exacto/semántico/híbrido + filtros facetados;
documentos similares; autocompletado; exportar ZIP+CSV; reportes.

**Independent Test**: Clasificar 100 docs, buscar texto de 3 por contenido,
filtrar por área, exportar ZIP+CSV, verificar integridad. Buscar por
concepto y validar que la semántica encuentra docs sin las palabras exactas.

### Tests for User Story 4 ⚠️

- [ ] T079 [P] [US4] Contract test `GET /documents/search` (modos hibrido/exacto/semantico + filtros) en `backend/tests/contract/test_search.py`
- [ ] T080 [P] [US4] Contract test `GET /documents/{id}/similar` y `GET /search/suggest` en `backend/tests/contract/test_search_extra.py`
- [ ] T081 [P] [US4] Contract test `POST /exports` y `GET /reports/stats` en `backend/tests/contract/test_exports_reports.py`
- [ ] T082 [P] [US4] Integration test búsqueda híbrida (keyword + semántica + facetada) en `backend/tests/integration/test_us4_search.py`

### Implementation for User Story 4

- [ ] T083 [US4] Implementar `backend/src/clasifica/services/search.py` (full-text tsvector español + trgm; semántica pgvector coseno; score híbrido α configurable; filtros facetados) — pasa T079
- [ ] T084 [US4] Endpoints `GET /documents/search`, `/documents/{id}/similar`, `/search/suggest` en `backend/src/clasifica/api/routes/search.py` — pasa T079, T080
- [ ] T085 [P] [US4] Implementar `backend/src/clasifica/services/exporter.py` (ZIP de PDFs + CSV metadatos) y tarea Celery de export
- [ ] T086 [US4] Endpoint `POST /exports` + `GET /reports/stats` en `backend/src/clasifica/api/routes/exports.py` — pasa T081, T082
- [ ] T087 [P] [US4] Frontend: feature `explorer` (árbol año→área→tipo, barra de búsqueda con modo, filtros facetados, autocompletado, resultados con snippets) en `frontend/src/features/explorer/`
- [ ] T088 [P] [US4] Frontend: componente "documentos similares" en `frontend/src/features/document/` + botón export
- [ ] T089 [P] [US4] E2E Playwright búsqueda + export en `frontend/tests/e2e/us4_search_export.spec.ts`

**Checkpoint**: US1-US4 funcionan independientemente.

---

## Phase 7: User Story 5 - Configuración de taxonomía y prompts (Priority: P5)

**Goal**: Admin configura áreas, tipos, esquema de correlativo, prompts LLM
y reglas de anonimización vía UI; exporta/importa config YAML.

**Independent Test**: Crear un tipo nuevo con su plantilla de correlativo,
procesar un PDF de ese tipo, verificar que se clasifica y nombra bien.

### Tests for User Story 5 ⚠️

- [ ] T090 [P] [US5] Contract test config `GET/POST/PUT /config/areas`, `/config/tipos` en `backend/tests/contract/test_config_taxonomia.py`
- [ ] T091 [P] [US5] Contract test `/config/correlativo`, `/config/llm`, `/config/anonimizacion`, `/config/export` (YAML) en `backend/tests/contract/test_config_avanzada.py`

### Implementation for User Story 5

- [ ] T092 [US5] Router `backend/src/clasifica/api/routes/config.py` (CRUD áreas/tipos, PUT correlativo/llm/anonimización, export/import YAML) — pasa T090, T091
- [ ] T093 [P] [US5] Frontend: feature `config` (gestión áreas/tipos, editor de plantilla correlativo, editor prompt LLM, reglas anonimización, export/import YAML) en `frontend/src/features/config/`
- [ ] T094 [P] [US5] E2E Playwright configuración en `frontend/tests/e2e/us5_config.spec.ts`

**Checkpoint**: Todas las user stories (US1-US5) funcionan independientemente.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Mejoras que afectan múltiples user stories.

- [ ] T095 [P] [POLISH] Manejo de edge cases: PDF corrupto/vacío (bandeja error), multi-página tipos distintos (marca revisión), reproceso mismo hash (link), API LLM caída (encola "esperando LLM") en `backend/src/clasifica/services/classifier.py`
- [ ] T096 [P] [POLISH] Script `backend/scripts/eval_classifier.py` (precisión por tipo/área, matriz confusión, p50/p95) sobre `tests/fixtures/` + `expected_classifications.json`
- [ ] T097 [P] [POLISH] Generar dataset de fixtures: `tests/fixtures/pdfs/` (PDFs sintéticos de cada tipo) + ground truth, versionado con DVC
- [ ] T098 [P] [POLISH] Documentación: actualizar `README.md` del backend/frontend + guía de operador (no técnico)
- [ ] T099 [POLISH] Seguridad: rate limiting API, revisión de headers, secrets solo por env, auditoría de logs
- [ ] T100 [POLISH] Performance: verificar SC-002 (p95 ≤15s), SC-003 (1000 docs ≤4h), SC-004 (búsqueda ≤2s en 100k)
- [ ] T101 [POLISH] Ejecutar validación completa de `quickstart.md` en entorno limpio (docker compose up desde cero)
- [ ] T102 [P] [POLISH] Cobertura de tests ≥80% backend (pytest-cov), corregir gaps

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — empieza de inmediato.
- **Foundational (Phase 2)**: depende de Setup — **BLOQUEA todas las US**.
- **User Stories (Phases 3-7)**: dependen de Foundational.
  - US1 (P1) es el MVP; recomendado primero.
  - US2-US5 pueden ir en paralelo tras Foundational (si hay equipo) o
    secuencial por prioridad (P1→P2→P3→P4→P5).
- **Polish (Phase 8)**: depende de las US deseadas completas.

### User Story Dependencies

- **US1 (P1)**: solo Foundational. Sin dependencias de otras US.
- **US2 (P2)**: Foundational. Reusa `process_document` de US1 pero es
  independientemente testeable.
- **US3 (P3)**: Foundational + la corrección de US1 (T056) para el feedback.
- **US4 (P4)**: Foundational + embeddings (T038) generados por el pipeline.
- **US5 (P5)**: Foundational. Independiente.

### Within Each User Story

- Tests escritos y en FALLO antes de implementar (TDD, constitución VI).
- Modelos → servicios → endpoints → frontend.
- Story completa antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Todas las tareas [P] de Setup en paralelo.
- Modelos T016-T025 en paralelo (archivos distintos).
- Tests de una US marcados [P] en paralelo.
- Frontend y backend de una misma US en paralelo tras definir schemas.
- US2-US5 en paralelo por distintos desarrolladores tras Foundational.

---

## Parallel Example: Foundational Models

```bash
# Lanzar todos los modelos juntos (archivos distintos):
Task: "Modelo Usuario en backend/src/clasifica/db/models/usuario.py"
Task: "Modelo Area en backend/src/clasifica/db/models/area.py"
Task: "Modelo TipoDocumental en .../tipo_documental.py"
Task: "Modelo Documento en .../documento.py"
# ... T016-T025
```

## Parallel Example: User Story 1 Tests

```bash
Task: "Contract test auth en backend/tests/contract/test_auth.py"
Task: "Contract test upload en backend/tests/contract/test_documents_upload.py"
Task: "Contract test classify en backend/tests/contract/test_classify.py"
Task: "Integration test flujo US1 en backend/tests/integration/test_us1_upload_flow.py"
```

---

## Implementation Strategy

### MVP First (Setup + Foundational + US1)

1. Phase 1: Setup
2. Phase 2: Foundational (CRÍTICO — bloquea todo)
3. Phase 3: User Story 1
4. **PARAR y VALIDAR**: probar US1 de extremo a extremo (subir PDF real
   de una municipalidad, verificar clasificación + correlativo + ubicación).
5. Demo del MVP.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. + US1 → demo MVP (carga individual en tiempo real).
3. + US2 → migración masiva de históricos.
4. + US3 → bandeja de revisión + feedback loop.
5. + US4 → búsqueda inteligente + exportación.
6. + US5 → configuración de taxonomía.

Cada story agrega valor sin romper las anteriores.

### Política de push (solicitada por el usuario)

Tras completar **cada fase** (Setup, Foundational, cada User Story, Polish):
`git commit` + `git push origin main` al repo `JoseLuisQL/clasifica-doc-muni`.

---

## Notes

- **Total**: 102 tareas. MVP (Setup+Foundational+US1) = T001-T063 (63 tareas).
- [P] = archivos distintos, sin dependencias.
- [Story] mapea la tarea a su user story para trazabilidad.
- TDD: verificar que los tests fallan antes de implementar.
- Commit tras cada tarea o grupo lógico; push tras cada fase.
- Parar en cualquier checkpoint para validar la story independientemente.
- Evitar: tareas vagas, conflictos en mismo archivo, dependencias
  cross-story que rompan la independencia.
