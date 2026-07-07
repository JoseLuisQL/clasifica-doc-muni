# ClasificaDocMuni

Sistema **on-premise** de clasificación automática de documentos PDF
escaneados para **municipalidades distritales del Perú**.

Pipeline: upload → OCR (español) → anonimización PII → **LLM multimodal**
(Qware `gemini-3-flash-agent`, API OpenAI-compatible) → asignación de
**correlativo** `NNNN-AREA-AÑO-TIPO` (secuencia al inicio) → renombrado +
organización física en `/AÑO/AREA/TIPO/NNNN-AREA-AÑO-TIPO-ASUNTO.pdf` →
indexación full-text **+ embeddings semánticos locales** → UI de revisión
y exploración con **búsqueda inteligente** (keyword + semántica +
facetada).

Soporta **carga individual en tiempo real** (≤15s p95) y **migración
masiva** de archivos históricos vía colas Celery. Precarga un **catálogo
TUPA base** (~40 áreas, ~50 tipos) según la Ley 27972, ajustable por
cada municipalidad.

## Stack

- **Backend**: Python 3.12, FastAPI, Celery, SQLAlchemy 2 (async), Alembic.
- **Frontend**: React 18, Vite, TanStack Query/Router, Tailwind + shadcn/ui.
- **Datos**: PostgreSQL 16 (full-text español + trigramas + **pgvector**
  para búsqueda semántica), Redis.
- **OCR**: PaddleOCR (español) + pdfplumber (texto nativo).
- **LLM (clasificación)**: Qware `gemini-3-flash-agent`, API externa
  OpenAI-compatible, con anonimización PII previa.
- **Embeddings (búsqueda semántica)**: `sentence-transformers`
  multilingüe local on-premise — no depende del proveedor LLM.
- **Despliegue**: Docker Compose on-premise.

## Documentación del proyecto (Spec-Driven Development)

Este proyecto sigue [spec-kit](https://github.com/github/spec-kit) de
GitHub. Artefactos en `specs/`:

- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) —
  principios rectores del proyecto.
- [`specs/001-clasificacion-documentos-municipales/spec.md`](specs/001-clasificacion-documentos-municipales/spec.md) —
  especificación funcional (user stories, requisitos, criterios).
- [`specs/001-clasificacion-documentos-municipales/plan.md`](specs/001-clasificacion-documentos-municipales/plan.md) —
  plan técnico de implementación.
- [`specs/001-clasificacion-documentos-municipales/research.md`](specs/001-clasificacion-documentos-municipales/research.md) —
  investigación de stack y alternativas.
- [`specs/001-clasificacion-documentos-municipales/data-model.md`](specs/001-clasificacion-documentos-municipales/data-model.md) —
  modelo de datos PostgreSQL.
- [`specs/001-clasificacion-documentos-municipales/quickstart.md`](specs/001-clasificacion-documentos-municipales/quickstart.md) —
  despliegue en 10 minutos.
- [`specs/001-clasificacion-documentos-municipales/contracts/`](specs/001-clasificacion-documentos-municipales/contracts/) —
  contratos: OpenAPI, LLM (Qware), estructura de carpetas, **catálogo
  TUPA base** (áreas + tipos documentales según Ley 27972).

## Flujo Spec-Driven (siguientes pasos)

El proyecto está inicializado con spec-kit. Para continuar el desarrollo
con un agente de coding (OpenCode/Copilot/Claude Code):

```bash
cd clasifica-doc-muni
# Los slash commands /speckit.* ya están disponibles en .opencode/commands/
```

1. `/speckit.clarify` — (opcional, recomendado) aclarar las preguntas
   abiertas marcadas como `NEEDS CLARIFICATION` / `Open Questions` en la spec.
2. `/speckit.tasks` — generar el desglose de tareas accionables desde el plan.
3. `/speckit.analyze` — validación de consistencia cross-artefacto.
4. `/speckit.implement` — ejecución TDD de las tareas.
5. `/speckit.converge` — reconciliar implementación vs. spec al final.

## Decisiones clave (resumen)

| Decisión | Valor |
|----------|-------|
| Despliegue | On-premise, Docker Compose |
| Clasificación | LLM multimodal Qware `gemini-3-flash-agent` (API OpenAI-compatible) |
| Búsqueda inteligente | Full-text + semántica (embeddings locales + pgvector) + facetada |
| Stack | Python + FastAPI + React |
| Correlativo | `NNNN-AREA-AÑO-TIPO` (secuencia al inicio, configurable) |
| Nombre archivo | `NNNN-AREA-AÑO-TIPO-ASUNTO_SLUG.pdf` |
| Organización | Carpetas físicas `/AÑO/AREA/TIPO/` |
| Originales | Inmutables en `/originales/<hash>.pdf`, hardlink a clasificados |
| Dedup | Por SHA-256 |
| OCR | PaddleOCR español + pdfplumber (nativo) |
| Catálogo TUPA | Base precargado ~40 áreas + ~50 tipos (Ley 27972), editable |
| Idioma | Español peruano |
| Retención legal | Ninguna por ahora (MVP conserva indefinidamente) |
| Firma digital | No (fuera de alcance MVP) |
| Usuarios | Único (MVP), arquitectura preparada para RBAC |
| Integración | Sistema autónomo (MVP), API REST para futuras |

## Preguntas resueltas (Clarification 2026-07-07)

- **NQ-001**: Proveedor LLM = Qware (`https://api.qware.me/v1`),
  modelo `gemini-3-flash-agent`. Embeddings locales (Qware no tiene
  `/v1/embeddings`).
- **NQ-002**: Sin política de retención legal en el MVP.
- **NQ-003**: Sin firma digital.
- **NQ-004**: Catálogo TUPA base completo precargado, editable por
  municipalidad.

## Estado de implementación

**Implementación completa** (spec-kit `/speckit.implement`, las 8 fases):

| Fase | User Story | Estado |
|------|-----------|--------|
| 1. Setup | Monorepo, docker-compose, tooling | ✅ |
| 2. Foundational | Config, 12 modelos, migraciones, seed TUPA, servicios core, pipeline Celery | ✅ |
| 3. US1 (P1) | Carga individual en tiempo real (MVP) | ✅ |
| 4. US2 (P2) | Carga masiva + CLI de migración | ✅ |
| 5. US3 (P3) | Bandeja de revisión + feedback loop | ✅ |
| 6. US4 (P4) | Búsqueda inteligente híbrida + exportación | ✅ |
| 7. US5 (P5) | Configuración de taxonomía/prompts | ✅ |
| 8. Polish | Edge cases, eval, seguridad, cobertura ≥80% | ✅ |

**Tests**: 66 pasan (unit + contract + integration). Cobertura backend
**80%** (módulos runtime-only —workers, OCR PaddleOCR, search pgvector—
se validan por integración con Docker). Lint `ruff` limpio. Frontend
`tsc` + `vite build` OK. **18 endpoints** REST + WebSocket.

## Cómo correr

### Con Docker Compose (recomendado, stack completo)

```bash
cp .env.example .env      # completar LLM_API_KEY de Qware
docker compose -f infra/docker-compose.yml up -d
# API: http://localhost:8080  ·  login: admin / (ADMIN_PASSWORD del .env)
```

Ver [`specs/001-clasificacion-documentos-municipales/quickstart.md`](specs/001-clasificacion-documentos-municipales/quickstart.md).

### Desarrollo local

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[ocr,dev]"
pytest                        # 66 tests, cobertura ≥80%
ruff check src/               # lint
uvicorn clasifica.main:app --reload   # requiere PostgreSQL+Redis

# Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173 (proxy a :8000)
npm run build                 # producción
```

### Evaluación del clasificador

```bash
cd backend
python -m clasifica.eval_classifier tests/fixtures/pdfs tests/fixtures/expected_classifications.json
```

## Estructura del código

```
backend/src/clasifica/
├── config.py, main.py           # settings, app factory (health, WS, CORS)
├── db/models/                   # 12 modelos SQLAlchemy (UUID/JSON portables)
├── db/seeds/                    # catálogo TUPA (46 áreas, 47 tipos) + loader
├── api/routes/                  # auth, documents, search, migration, exports, config, reports
├── schemas/                     # DTOs Pydantic
├── services/                    # dedup, ocr, anonymize, llm_client (Qware),
│                                #   embeddings (local), correlativo, organizer,
│                                #   classifier, search (híbrida), exporter
├── core/                        # security (JWT), logging (JSON), errors
├── workers/                     # Celery: process_document, batch_migration
├── cli/                         # migrate, jobs, seed
└── eval_classifier.py           # métricas de precisión
frontend/src/
├── api/, stores/                # cliente axios + Zustand
└── features/                    # auth, upload, migration, review, explorer, config
```

## Licencia

Por definir.
