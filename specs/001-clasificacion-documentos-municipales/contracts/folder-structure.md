# Folder Structure Contract

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07

Contrato de la estructura física de archivos en disco. El organizador
(`backend/src/clasifica/services/organizer.py`) DEBE cumplir este
contrato; los tests de contrato lo validan.

## Layout raíz

```
${DATA_DIR}/                              # default: /var/clasifica/data
├── originales/                           # INMUTABLE. Nunca se modifica ni borra.
│   └── AB/CD/                            # 2 primeros / 2 siguientes chars del hash
│       └── ABCD...XYZ.pdf                # nombre = hash completo .pdf
├── documentos/                           # estructura clasificada (hardlinks a originales)
│   └── {AÑO}/
│       └── {AREA_CODIGO}/
│           └── {TIPO_CODIGO}/
│               └── {CORRELATIVO}-{ASUNTO_SLUG}.pdf
│                  # ej: 0001-GDE-2026-INF-informe-solicitud-licencia.pdf
│                  # correlativo = NNNN-AREA-AÑO-TIPO (secuencia AL INICIO)
│                  # asunto_slug = versión limpia del asunto (lowercase, guiones, máx 60 chars)
├── tmp/
│   ├── ocr/                              # OCR intermediarios, purga 7 días
│   ├── preprocess/                       # imágenes preprocesadas
│   ├── embeddings/                       # cache de modelos sentence-transformers
│   └── uploads/                          # uploads en curso
└── backups/                              # exports generados (purga 30 días)
```

## Formato del nombre de archivo

`{CORRELATIVO}-{ASUNTO_SLUG}.pdf`

- **CORRELATIVO**: secuencia al inicio. Default:
  `{SEQ:04d}-{AREA}-{AÑO}-{TIPO}` → ej: `0001-GDE-2026-INF`.
  Configurable en `configuracion_correlativo.plantilla`.
- **ASUNTO_SLUG**: derivado del asunto extraído por el LLM, saneado:
  - lowercase
  - sin acentos ni caracteres especiales
  - palabras separadas por guiones
  - truncado a 60 caracteres
  - ej: "Informe sobre Solicitud de Licencia de Construcción" →
    `informe-sobre-solicitud-de-licencia-de-construccion`

Ejemplo completo:
`0001-GDE-2026-INF-informe-sobre-solicitud-de-licencia-de-construccion.pdf`

El correlativo al inicio garantiza **orden natural** de los archivos en
el explorador del sistema operativo (0001, 0002, ... agrupados por
carpeta año/área/tipo).

## Reglas

1. **`originales/`** es la fuente de verdad. Se escribe una sola vez al
   cargar un documento (nombre = `hash_sha256 + ".pdf"`). Nunca se
   renombra, mueve, ni borra. El operador NO debe tocar esta carpeta.
2. **`documentos/`** contiene **hardlinks** a los originales (no copias),
   organizados por año/área/tipo, con nombre = correlativo. Si el
   filesystem no soporta hardlink cross-device, se copia y se loguea.
3. **Hash sharding**: `originales/AB/CD/<hash>.pdf` para evitar
   directorios con >10k archivos (mejora `readdir`).
4. **Carpetas año/área/tipo**: se crean bajo demanda al clasificar el
   primer documento de esa combinación. No se pre-crean.
5. **Renombrado al corregir**: si el operador corrige área/tipo/año, el
   hardlink viejo se elimina y se crea uno nuevo en la nueva ruta con el
   nuevo correlativo. El original en `originales/` no se toca.
6. **Re-clasificación**: misma lógica que corrección; el evento
   `renombrado` registra `ruta_anterior` y `ruta_nueva`.
7. **Exportación**: los ZIP de exportación van a `tmp/backups/` y se
   sirven al frontend como descarga; purga automática a los 30 días.
8. **Permisos filesystem**: `originales/` lectura-only para el contenedor
   de workers (uid 1000); `documentos/` lectura-escritura; `tmp/`
   lectura-escritura.

## Ejemplo concreto

Documento: oficio de la Gerencia de Infraestructura, año 2026, primer
oficio del año.

- Hash: `a1b2c3d4e5...`
- Original: `originales/a1/b2/a1b2c3d4e5....pdf`
- Clasificado: `documentos/2026/GER-INF/OFC/GER-INF-2026-OFC-0001.pdf`
- En BD: `documentos.ruta_original` y `documentos.ruta_clasificada`.

## Validación de contrato (test)

`backend/tests/contract/test_folder_structure.py` verifica tras procesar
un set de documentos:

- Todo documento clasificado tiene `ruta_clasificada` que existe y cumple
  `documentos/{AÑO}/{AREA}/{TIPO}/{CORRELATIVO}.pdf`.
- El `ruta_original` existe en `originales/{2}/{2}/{hash}.pdf`.
- `ruta_clasificada` y `ruta_original` apuntan al mismo inodo (hardlink)
  cuando el filesystem lo soporta.
- No hay archivos huérfanos en `documentos/` sin fila correspondiente en BD.
- `originales/` no contiene duplicados (cada hash aparece una vez).
