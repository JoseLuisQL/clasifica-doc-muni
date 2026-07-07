# ClasificaDocMuni — Constitution

Sistema de clasificación automática de documentos PDF escaneados para
municipalidades distritales del Perú. On-premise, autónomo, con
clasificación por LLM multimodal vía API OpenAI-compatible.

## Core Principles

### I. Soberanía de datos local
Los PDFs originales, sus metadatos, la base de datos, el almacén de
archivos clasificados y **los embeddings semánticos** viven **dentro**
del servidor de la municipalidad. El único componente que sale del
perímetro es el contenido textual/visual enviado al LLM externo (Qware)
para clasificación — y debe pasar por una etapa de **anonimización** de
PII sensible (DNI, RUC, firmas, datos biométricos) antes de enviarse.
Los **embeddings para búsqueda semántica se generan localmente**
(sentence-transformers on-premise), nunca vía el proveedor LLM. El
operador puede auditar qué se envió en cada caso.

### II. Clasificación determinista y explicable
Toda clasificación debe registrar: prompt enviado, respuesta del LLM,
modelo usado, confianza reportada y reglas posteriores aplicadas. El
operador puede revisar y revertir cualquier decisión. El correlativo se
asigna por reglas deterministas (área + año + tipo + secuencia) — nunca
lo decide el LLM.

### III. Idempotencia y trazabilidad
Procesar el mismo PDF dos veces produce el mismo correlativo (deduplicación
por hash SHA-256). Cada documento tiene una cadena de eventos auditable
(cargado, OCR, clasificado, renombrado, movido, revertido, re-clasificado).
Nada se destruye: el archivo original se conserva en un almacén inmutable
`/originales/` y el renombrado es un hardlink/copia, nunca un movimiento
destructivo.

### IV. Tiempo real + lote, misma tubería
El pipeline de procesamiento (upload → OCR → extracción → clasificación →
correlativo → organización → indexación) es **uno solo**. El modo
interactivo (1 documento, respuesta en <15s) y el modo migración masiva
(miles de documentos históricos vía watch-folder/CLI) comparten colas y
workers. Diferir solo en prioridad, no en lógica.

### V. Configuración sobre código
Tipos de documento, áreas, esquema de correlativo, palabras clave,
plantillas de prompt y reglas de anonimización son **datos** en tablas/
archivos YAML, no constantes en código. Una municipalidad configura su
propia taxonomía sin tocar el código. El LLM recibe la taxonomía vigente
en cada llamada.

### VI. Test-first (NO NEGOCIABLE)
TDD estricto. Para cada módulo: tests escritos y aprobados → tests fallan
→ implementación → verde. Cobertura mínima 80% en `backend/src`.
Dataset de PDFs de prueba (sintéticos + muestras anonimizadas) en
`tests/fixtures/` versionado con DVC para reproducibilidad del modelo.

### VII. Simpson y operable
El operador de archivo de la municipalidad (no un ingeniero) debe poder
instalarlo, configurarlo, corregir clasificaciones y migrar archivos sin
tocar la terminal. Todo lo crítico tiene UI. CLI solo para migraciones
masivas y mantenimiento.

## Restricciones de cumplimiento

- **Idioma**: español peruano. UI, logs, prompts y reportes en español.
- **Normativa**: compatible con la Ley N° 29733 (Protección de Datos
  Personales del Perú) y la Directiva de Gestión Documental del MINTRAB.
  Retención configurable por tipo documental.
- **OCR**: español como idioma principal; tolerancia a nombres propios
  quechuas/aymaras transliterados.
- **Hardware objetivo**: servidor Linux x86_64, 16GB RAM mínimo (32GB
  recomendado), 500GB disco. Sin GPU requerida (el LLM es externo; los
  embeddings locales corren en CPU con modelos ligeros ~120MB).
- **Conectividad**: el sistema opera offline para consulta/organización/
  búsqueda (incluida la búsqueda semántica, que es local); solo la
  clasificación LLM requiere conectividad saliente a la API de Qware.
  Si la API cae, los documentos quedan encolados y se procesan al recuperar.

## Flujo de desarrollo

1. Constitution (este archivo) — ratificado antes de cualquier spec.
2. `/speckit.specify` — especificación funcional por feature.
3. `/speckit.clarify` — aclarar ambigüedades antes del plan.
4. `/speckit.plan` — plan técnico + research + data-model + contracts.
5. `/speckit.tasks` — desglose en tareas accionables.
6. `/speckit.implement` — ejecución TDD.
7. `/speckit.converge` — reconciliar implementación vs. spec.

Cada feature en su rama `NNN-feature-name`. Merge a `main` solo tras
pasar tests + checklist de aceptación de la spec.

## Governance

La constitución tiene prioridad sobre cualquier otra decisión. Cualquier
excepción debe justificarse en `Complexity Tracking` del plan y
documentarse. Para decisiones de implementación en runtime, ver
`.specify/memory/constitution.md` (este archivo).

**Version**: 1.0.0 | **Ratified**: 2026-07-07 | **Last Amended**: 2026-07-07
