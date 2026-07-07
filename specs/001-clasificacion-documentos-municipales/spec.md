# Feature Specification: Clasificación Automática de Documentos Municipales

**Feature Branch**: `001-clasificacion-documentos-municipales`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Sistema automático de clasificación de
documentos PDF escaneados en carpetas y asignación de nombre según su
contenido. Documentos institucionales de trámites de municipalidades
distritales del Perú (informes, cartas, memorandos, resoluciones,
ordenanzas, decretos, TUPA, actas, denuncias). Carga individual o
masiva, clasificación en tiempo real, organización por año/área/tipo,
asignación de correlativo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Carga individual con clasificación en tiempo real (Priority: P1)

El operador de archivo inicia sesión en la web, arrastra un PDF escaneado
a la zona de carga, y en menos de 15 segundos ve: el texto extraído
(OCR), el tipo detectado (con % confianza), el área sugerida, el asunto
extraído, el año detectado, y el correlativo propuesto. Puede confirmar
o corregir cualquier campo. Al confirmar, el PDF se renombra al
correlativo, se mueve a `/AÑO/AREA/TIPO/CORRELATIVO.pdf`, se indexa en
la base de datos y aparece en el explorador de documentos.

**Why this priority**: Es el flujo central y el valor mínimo viable.
Sin esto no hay producto. Demuestra de extremo a extremo OCR → LLM →
correlativo → organización.

**Independent Test**: Subir un único PDF de informe escaneado de muestra
y verificar que se clasifica, renombra y ubica correctamente en la
estructura de carpetas, con todos los metadatos visibles en la UI.

**Acceptance Scenarios**:

1. **Given** un operador autenticado, **When** arrastra un PDF escaneado
   de un "Informe" de la "Gerencia de Desarrollo Económico" a la zona de
   carga, **Then** en ≤15s el sistema muestra: OCR, tipo=Informe (conf
   ≥85%), área=Gerencia de Desarrollo Económico, asunto extraído, año,
   y correlativo `GER-DES-2026-INF-0001`.
2. **Given** la clasificación propuesta, **When** el operador corrige el
   área a "Gerencia de Infraestructura", **Then** el correlativo se
   recalcula a `GER-INF-2026-INF-0001` y la confianza de la corrección
   se registra para reentrenamiento futuro.
3. **Given** un PDF ya clasificado, **When** el operador lo busca por
   asunto o correlativo en el explorador, **Then** lo encuentra, puede
   previsualizarlo, descargarlo y ver su historial de eventos.

---

### User Story 2 - Carga masiva de documentos históricos (Priority: P2)

El operador selecciona una carpeta (o arrastra cientos de PDFs) para
migrar archivos históricos. El sistema encola todos, procesa en paralelo
según capacidad, muestra una barra de progreso con estado por documento
(pendiente, procesando, clasificado, requiere revisión, error). Los
documentos con confianza <70% o conflictos de correlativo se marcan para
revisión humana en una bandeja. El operador puede pausar/reanudar la
migración.

**Why this priority**: Las municipalidades tienen años de archivos
físicos/digitales por migrar. Sin carga masiva, el valor del sistema se
limita a documentos nuevos. Es el segundo flujo más valioso.

**Independent Test**: Apuntar el sistema a una carpeta con 50 PDFs
históricos mixtos, ejecutar la migración, y verificar que todos quedan
clasificados o encolados para revisión, con un reporte final de
estadísticas (clasificados / revisión / errores).

**Acceptance Scenarios**:

1. **Given** una carpeta con 200 PDFs históricos, **When** el operador
   la selecciona para migración masiva, **Then** el sistema encola los
   200, procesa en paralelo (hasta N workers configurables), y muestra
   progreso en tiempo real con estado individual.
2. **Given** un documento con confianza de clasificación <70%,
   **When** termina de procesarse, **Then** aparece en la bandeja de
   revisión con la sugerencia del LLM y los campos editables.
3. **Given** una migración en curso, **When** el operador pausa, **Then**
   los workers en curso terminan su documento actual y no toman nuevos
   hasta reanudar; al reanudar continúa desde donde quedó.

---

### User Story 3 - Revisión y corrección de clasificaciones (Priority: P3)

El operador accede a la bandeja de revisión con documentos de baja
confianza, conflictos o duplicados. Para cada uno ve: el PDF, el OCR, la
sugerencia del LLM con justificación, y campos editables (tipo, área,
asunto, año). Al guardar, el documento se reubica, el correlativo se
recalcula si cambió área/tipo/año, y el caso se registra como muestra de
entrenamiento para mejorar futuras clasificaciones (feedback loop).

**Why this priority**: El LLM no es 100% preciso. Sin bandeja de
revisión, los errores se acumulan y minan la confianza en el sistema.
Habilita el feedback loop que mejora la precisión con el tiempo.

**Independent Test**: Generar 10 documentos con clasificación
deliberadamente ambigua, verificar que aparecen en la bandeja, corregir
5, y comprobar que se reubican correctamente y se registran para
reentrenamiento.

**Acceptance Scenarios**:

1. **Given** documentos en la bandeja de revisión, **When** el operador
   abre uno, **Then** ve PDF + OCR + sugerencia LLM + justificación +
   campos editables con la sugerencia pre-cargada.
2. **Given** el operador corrige el tipo de "Carta" a "Memorando",
   **When** guarda, **Then** el documento se renombra y reubica a la
   nueva carpeta `/AÑO/AREA/MEM/`, el correlativo se recalcula, y el
   caso queda etiquetado para reentrenamiento.

---

### User Story 4 - Exploración, búsqueda y exportación (Priority: P4)

El operador navega la estructura por año → área → tipo, o busca por
texto libre (sobre OCR + asunto + correlativo), filtros combinados
(rango fechas, área, tipo, confianza), y exporta resultados (ZIP de PDFs
+ CSV de metadatos). Genera reportes: documentos por área/mes,
clasificaciones corregidas, cola de migración.

**Why this priority**: Una vez clasificado el archivo, su valor está en
encontrarlo rápido y exportarlo para trámites/auditorías. Sin esto el
sistema es un depósito opaco.

**Independent Test**: Clasificar 100 documentos diversos, buscar por
texto que aparezca en el OCR de 3 de ellos, aplicar filtro por área,
exportar los resultados a ZIP+CSV, y verificar la integridad de la
exportación.

**Acceptance Scenarios**:

1. **Given** un repositorio con documentos clasificados, **When** el
   operador busca "permiso de obra", **Then** obtiene en <2s todos los
   documentos cuyo OCR/asunto coinciden, ordenados por relevancia.
2. **Given** una selección de documentos, **When** el operador exporta,
   **Then** se descarga un ZIP con los PDFs renombrados y un CSV con
   todos los metadatos (correlativo, tipo, área, asunto, fecha, ruta).

---

### User Story 5 - Configuración de taxonomía y prompts (Priority: P5)

El operador administrador configura: tipos de documento (con códigos y
plantillas de correlativo), áreas (con códigos), palabras clave por tipo,
plantillas de prompt del LLM, y reglas de anonimización. Cambios se
aplican a futuras clasificaciones sin redeploys. Exporta/importa la
configuración como YAML para replicar entre municipalidades.

**Why this priority**: Cada municipalidad tiene su propia estructura.
Sin configuración flexible, el producto no es replicable.

**Independent Test**: Crear un nuevo tipo "Constancia de Habitabilidad"
con código `CON-HAB`, plantilla de correlativo `AREA-AÑO-CON-HAB-NNNN`,
procesar un PDF de ese tipo, y verificar que se clasifica y nombra
correctamente con la nueva configuración.

**Acceptance Scenarios**:

1. **Given** la vista de configuración, **When** el admin añade un área
   "Gerencia de Medio Ambiente" con código `GER-MAM`, **Then** las
   siguientes clasificaciones pueden asignar documentos a esa área y el
   correlativo la usa.
2. **Given** la configuración, **When** el admin exporta, **Then** se
   descarga un YAML que, importado en otra instancia, reproduce la misma
   taxonomía.

---

### Edge Cases

- **PDF no escaneado (texto nativo)**: el sistema detecta si el PDF ya
  tiene texto extraíble y omite/salta el OCR, usándolo directo.
- **PDF multi-página con tipos distintos**: un PDF puede contener un
  oficio y su anexo (informe). El sistema clasifica por la primera
  página/portada y marca el caso para revisión.
- **PDF corrupto o vacío**: se marca como error, no se asigna
  correlativo, va a bandeja de errores.
- **PDF escaneado con mala calidad (OCR con confianza baja)**: se
  reintenta con preprocesamiento (deskew, binarización, upscaling) y si
  sigue bajo umbral, se marca para revisión.
- **Conflicto de correlativo (dos PDFs que el LLM clasifica igual en
  mismo área/año/tipo)**: el segundo recibe el siguiente correlativo
  disponible; ambos se registran con timestamps; no hay colisión.
- **Reproceso de un PDF ya clasificado (mismo hash)**: se detecta por
  SHA-256 y se enlaza al documento existente en lugar de duplicar.
- **API del LLM caída**: los documentos se encolan, se reintenta con
  backoff exponencial, y el operador ve el estado "esperando LLM".
- **Documento en quechua**: el OCR puede extraer texto; el LLM se
  configura para detectar idioma y marcar el documento.
- **Cambio de configuración de taxonomía con documentos ya
  clasificados**: los existentes conservan su clasificación; solo futuros
  documentos usan la nueva configuración.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST aceptar carga individual de PDF vía
  drag&drop en la web y procesar en ≤15s (p95) para documentos de hasta
  50 páginas.
- **FR-002**: El sistema MUST aceptar carga masiva vía selección de
  carpeta o multi-archivo, encolando y procesando en paralelo con
  progreso en tiempo real.
- **FR-003**: El sistema MUST realizar OCR en español sobre PDFs
  escaneados, detectando y omitiéndolo si el PDF ya tiene texto nativo.
- **FR-004**: El sistema MUST enviar el contenido (texto OCR + imagen de
  primera página) a un LLM multimodal vía API OpenAI-compatible para
  clasificar tipo documental, área, asunto y año, con score de confianza.
- **FR-005**: El sistema MUST anonimizar PII sensible (DNI, RUC, firmas,
  datos biométricos) del contenido enviado al LLM, con registro auditable
  de qué se anonimizó.
- **FR-006**: El sistema MUST asignar correlativo con formato configurable
  `NNNN-AREA-AÑO-TIPO` (default), con la **secuencia numérica al inicio**
  para orden natural de archivos. Secuencia atómica por combinación
  área+año+tipo, a prueba de concurrencia.
- **FR-007**: El sistema MUST renombrar el PDF al correlativo y ubicarlo
  físicamente en `/AÑO/AREA/TIPO/CORRELATIVO.pdf`, conservando el
  original en `/originales/HASH.pdf`.
- **FR-008**: El sistema MUST deduplicar por SHA-256: si un PDF con el
  mismo hash ya fue procesado, se enlaza al existente en vez de duplicar.
- **FR-009**: El sistema MUST mantener un log auditable por documento:
  cargado, OCR, LLM (prompt+respuesta+modelo+confianza), correlativo
  asignado, renombrado, movido, revertido, re-clasificado.
- **FR-010**: El sistema MUST proporcionar una bandeja de revisión para
  documentos con confianza <70%, conflictos o duplicados, con edición
  manual y feedback loop para reentrenamiento.
- **FR-011**: El sistema MUST permitir búsqueda por **asunto**, por
  **documento** (correlativo/tipo/área/año) y por **contenido** (full-text
  sobre el OCR), con filtros facetados combinables (área, tipo, año,
  rango de fechas, confianza, estado, origen).
- **FR-011a**: El sistema MUST proveer **búsqueda semántica inteligente**:
  además de la búsqueda por palabras clave, debe encontrar documentos
  por concepto/significado aunque no contengan las palabras exactas
  (ej. buscar "permisos de obra" encuentra licencias de edificación).
  Implementada con embeddings locales (sentence-transformers
  multilingüe) almacenados en pgvector, sin depender del proveedor LLM.
- **FR-011b**: El sistema MUST ofrecer **"documentos similares"**: desde
  cualquier documento, encontrar los más parecidos por contenido/asunto
  vía similitud coseno sobre embeddings.
- **FR-011c**: El sistema MUST proveer autocompletado de asuntos y
  sugerencias de áreas/tipos al escribir en la barra de búsqueda.
- **FR-012**: El sistema MUST permitir exportar selecciones a ZIP (PDFs)
  + CSV (metadatos) y generar reportes estadísticos.
- **FR-013**: El sistema MUST permitir configurar tipos documentales,
  áreas, esquemas de correlativo, plantillas de prompt y reglas de
  anonimización vía UI, aplicable a futuras clasificaciones sin redeploy.
- **FR-014**: El sistema MUST operar offline para consulta/búsqueda/
  organización; solo la clasificación LLM requiere conectividad saliente.
  Documentos encolados si la API no responde, procesados al recuperar.
- **FR-015**: El sistema MUST soportar autenticación de usuario único
  (MVP) con credenciales locales; arquitectura preparada para RBAC
  multi-usuario futuro.
- **FR-016**: El sistema MUST detectar PDFs multi-página con tipos
  distintos y marcarlos para revisión.
- **FR-017**: El sistema MUST permitir pausar/reanudar migraciones
  masivas sin perder estado.
- **FR-018**: El sistema MUST preprocesar PDFs de baja calidad OCR
  (deskew, binarización, upscale) antes de reintentar.
- **FR-019**: El sistema MUST exponer una API REST documentada (OpenAPI)
  para integraciones futuras (mesa de partes, SISGEDO).
- **FR-020**: El sistema MUST registrar muestras de corrección humana
  (documento + clasificación corregida) para reentrenamiento futuro del
  clasificador.

### Key Entities *(include if feature involves data)*

- **Documento**: PDF procesado o encolado. Atributos: id, hash SHA-256,
  correlativo, tipo, área, asunto, año, fecha documento, ruta original,
  ruta clasificada, estado (pendiente/procesando/clasificado/revisión/
  error), confianza, fecha carga, origen (interactivo/migración).
- **EventoDocumento**: entrada en el log auditable de un documento.
  Atributos: id documento, timestamp, tipo evento, payload JSON (prompt
  LLM, respuesta, modelo, diff de corrección, etc.).
- **TipoDocumental**: tipo configurado. Atributos: código, nombre, área
  típica, plantilla correlativo, palabras clave, descripción para prompt.
- **Area**: área municipal configurada. Atributos: código, nombre,
  jerarquía (gerencia/subgerencia), activa.
- **ConfiguracionCorrelativo**: esquema de numeración. Atributos:
  plantilla (ej. `{AREA}-{AÑO}-{TIPO}-{SEQ}`), relleno de secuencia,
  reinicio anual.
- **SecuenciaCorrelativo**: contador atómico por (área, año, tipo).
  Atributos: área, año, tipo, último valor. Actualización transaccional.
- **MuestraEntrenamiento**: corrección humana registrada. Atributos:
  id documento, clasificación original, clasificación corregida,
  operador, timestamp, texto OCR, usado_en_reentrenamiento.
- **ConfiguracionLLM**: endpoint, modelo, API key (referenciada, no en
  código), temperatura, max_tokens, plantilla de prompt.
- **ColaProcesamiento**: job de procesamiento de un documento.
  Atributos: id documento, estado (queued/processing/done/failed/
  paused), prioridad, intentos, worker asignado, timestamps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ≥90% de documentos de prueba clasificados correctamente
  (tipo+área) en primera pasada sin corrección humana.
- **SC-002**: Tiempo p95 de procesamiento de un documento individual
  ≤15s (incluye OCR + LLM + organización).
- **SC-003**: Migración de 1000 documentos en ≤4 horas en servidor
  objetivo (16 workers).
- **SC-004**: Búsqueda full-text retorna resultados en ≤2s sobre un
  repositorio de 100k documentos.
- **SC-005**: Cero colisiones de correlativo bajo carga concurrente
  (10 uploads simultáneos misma área/año/tipo).
- **SC-006**: Deduplicación por hash detecta 100% de reintentos del
  mismo PDF.
- **SC-007**: Operador no técnico completa el flujo de carga+corrección
  sin tocar la terminal tras una capacitación de 1 hora.
- **SC-008**: El sistema opera consultas/búsquedas 100% offline; la
  caída de la API LLM no bloquea consultas ni organiza documentos ya
  clasificados.

## Assumptions

- La municipalidad provee un servidor Linux (Ubuntu 22.04+ recomendado)
  con 16GB RAM mínimo, 500GB disco, conectividad saliente a internet
  para la API LLM.
- La API LLM externa es OpenAI-compatible (soporta `/v1/chat/completions`
  con visión) y la municipalidad gestiona su propia API key y facturación.
- Los PDFs de entrada son legibles para un humano; el sistema no
  garantiza clasificación sobre PDFs completamente ilegibles.
- MVP: usuario único. La arquitectura (JWT, tablas con `usuario_id`)
  queda preparada para RBAC multi-usuario en una fase posterior.
- MVP: sistema autónomo, sin integraciones con SISGEDO/mesa de partes;
  se expone API REST para futuras integraciones.
- Los documentos físicos ya están digitalizados a PDF; la digitalización
  desde papel está fuera de alcance.
- Se cuenta con un set inicial de ~50-100 PDFs de muestra anonimizados
  por la municipalidad para calibrar prompts y validar precisión.
- El operador de archivo conoce la estructura organizacional de la
  municipalidad (áreas, tipos documentales) y puede configurarlos.

## Decisions Resolved (Clarification 2026-07-07)

- **NQ-001 (Proveedor LLM) — RESUELTO**: Proveedor **Qware**
  (`https://api.qware.me/v1`), modelo **`gemini-3-flash-agent`**.
  API OpenAI-compatible. La API key se gestiona como **secret** en
  variable de entorno `LLM_API_KEY` (nunca en código ni en el repo).
  Qware **no expone endpoint `/v1/embeddings`** (verificado: 404), por
  lo que la búsqueda semántica usa **embeddings locales** on-premise
  (sentence-transformers + pgvector).
- **NQ-002 (Retención legal) — RESUELTO**: Ninguna por ahora. No se
  implementa política de retención/purga legal por tipo documental en
  el MVP. Los documentos se conservan indefinidamente. Se deja hook de
  extensión (`politicas_retencion`) para una fase futura.
- **NQ-003 (Firma digital) — RESUELTO**: NO. Sin firma digital ni
  sellado de tiempo. Fuera de alcance del MVP.
- **NQ-004 (Catálogo de áreas y tipos) — RESUELTO**: Se provee un
  **catálogo base completo** según la Ley Orgánica de Municipalidades
  N° 27972 y el TUPA municipal genérico del Perú, en
  [`contracts/tupa-catalogo.md`](contracts/tupa-catalogo.md). Cubre ~40
  áreas (órganos de gobierno, dirección, gerencias de línea,
  subgerencias, unidades especiales) y ~50 tipos documentales (gestión
  interna, actos administrativos, TUPA, documentos ciudadanos, actas,
  contratos, control). Cada municipalidad lo ajusta vía UI.
