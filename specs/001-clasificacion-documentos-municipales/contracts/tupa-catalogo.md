# Catálogo TUPA Municipal Base — Municipalidades Distritales del Perú

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07

Catálogo base de áreas (estructura orgánica) y tipos documentales para
municipalidades distritales del Perú, según la **Ley Orgánica de
Municipalidades N° 27972** (art. 28), la práctica del TUPA municipal y
lineamientos del Archivo General de la Nación.

Este catálogo se carga como **seed inicial** de la base de datos
(`backend/src/clasifica/db/seeds/tupa_base.yaml`). Es **editable** vía UI
por cada municipalidad: cada entidad ajusta códigos, activa/desactiva
lo que no aplica, y añade sus propios tipos/subgerencias. No es
exhaustivo ni cerrado — es un punto de partida completo para que el
sistema funcione desde el día 1 en cualquier municipalidad distrital.

## Áreas (estructura orgánica)

Códigos cortos únicos. Jerarquía vía `padre_codigo`. El campo `orden`
define el orden de visualización.

### Órganos de Gobierno

| Código | Nombre | Padre | Tipo |
|--------|--------|-------|------|
| ALD | Alcaldía | — | gobierno |
| CCM | Concejo Municipal | — | gobierno |

### Alta Dirección y Órganos Básicos (art. 28 LOM)

| Código | Nombre | Padre | Tipo |
|--------|--------|-------|------|
| GRM | Gerencia Municipal | ALD | direccion |
| OCI | Órgano de Auditoría Interna | ALD | control |
| PPM | Procuraduría Pública Municipal | ALD | asesoria |
| ASJ | Oficina de Asesoría Jurídica | GRM | asesoria |
| PLP | Oficina de Planeamiento y Presupuesto | GRM | asesoria |
| SGE | Secretaría General | GRM | apoyo |
| OTD | Oficina de Trámite Documentario y Archivo (Mesa de Partes) | GRM | apoyo |
| OTI | Oficina de Tecnologías de la Información | GRM | apoyo |
| OCO | Oficina de Comunicaciones e Imagen | GRM | apoyo |
| ORH | Oficina de Recursos Humanos | GAF | apoyo |

### Gerencias de Línea

| Código | Nombre | Padre | Tipo |
|--------|--------|-------|------|
| GAF | Gerencia de Administración y Finanzas | GRM | linea |
| GIT | Gerencia de Infraestructura y Desarrollo Territorial | GRM | linea |
| GDE | Gerencia de Desarrollo Económico | GRM | linea |
| GDS | Gerencia de Desarrollo Social | GRM | linea |
| GSP | Gerencia de Servicios Públicos | GRM | linea |
| GAM | Gerencia de Gestión Ambiental | GRM | linea |
| GAT | Gerencia de Administración Tributaria | GRM | linea |
| GSC | Gerencia de Seguridad Ciudadana | GRM | linea |
| GPI | Gerencia de Obras / Proyectos de Inversión | GRM | linea |
| GTR | Gerencia de Transporte Público | GRM | linea |

### Subgerencias típicas (hijas de gerencias de línea)

| Código | Nombre | Padre |
|--------|--------|-------|
| SCT | Subgerencia de Contabilidad | GAF |
| STE | Subgerencia de Tesorería | GAF |
| SLO | Subgerencia de Logística y Abastecimiento | GAF |
| SCA | Subgerencia de Catastro | GIT |
| SHU | Subgerencia de Habilitaciones Urbanas | GIT |
| SLC | Subgerencia de Licencias de Construcción | GIT |
| SDB | Subgerencia de Desarrollo Urbano | GIT |
| SDEL | Subgerencia de Desarrollo Económico Local | GDE |
| SCM | Subgerencia de Comercialización y Mercados | GDE |
| STU | Subgerencia de Turismo | GDE |
| SED | Subgerencia de Educación | GDS |
| SCU | Subgerencia de Cultura | GDS |
| SDE | Subgerencia de Deporte y Recreación | GDS |
| SPS | Subgerencia de Programas Sociales | GDS |
| SLI | Subgerencia de Limpieza Pública y Recolección | GSP |
| SPJ | Subgerencia de Parques y Jardines | GSP |
| SCE | Subgerencia de Cementerio y Servicios Funerarios | GSP |
| STR | Subgerencia de Tributación y Rentas | GAT |
| SFI | Subgerencia de Fiscalización Tributaria | GAT |
| SMA | Subgerencia de Medio Ambiente | GAM |
| SSA | Subgerencia de Saneamiento y Salud Ambiental | GAM |

### Unidades Especiales (organismos municipales)

| Código | Nombre | Padre | Tipo |
|--------|--------|-------|------|
| DMN | DEMUNA (Defensoría del Niño y Adolescente) | GDS | especial |
| OMP | OMAPED (Atención a Personas con Discapacidad) | GDS | especial |
| CIM | CIM (Centro de Emergencia Mujer) | GSC | especial |
| CIS | CAVIT / Unidad de Violencia | GSC | especial |

## Tipos Documentales

Códigos cortos únicos. El `area_tipica` es solo una sugerencia por
defecto para el LLM; cualquier tipo puede asignarse a cualquier área.

### Documentos de Gestión Interna

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| INF | Informe | GRM | Documento por el que un servidor comunica información a un superior para conocimiento o decisión. Encabezado "INFORME". |
| INT | Informe Técnico | GIT | Informe de carácter técnico (obras, catastro, etc.) con conclusiones técnicas. |
| INL | Informe Legal | ASJ | Informe de carácter jurídico-legal emitido por Asesoría Jurídica. |
| MEM | Memorando | GRM | Comunicación interna entre unidades para instrucciones, información o pedidos. Encabezado "MEMORANDO". |
| MEC | Memorando Múltiple/Circular | GRM | Memorando dirigido a varios destinatarios simultáneamente. |
| OFI | Oficio | GRM | Comunicación oficial dirigida a otras entidades públicas o externas. Encabezado "OFICIO". |
| OFC | Oficio Circular | GRM | Oficio dirigido a múltiples destinatarios. |
| CAR | Carta | GRM | Comunicación formal de menor jerarquía que el oficio, a particulares o entidades. |
| NOT | Nota | GRM | Comunicación breve interna o externa. |
| PRO | Proveído / Providencia | GRM | Resolución interna de trámite que impulsa el procedimiento administrativo. |
| DIC | Dictamen | ASJ | Opinión técnico-legal de Asesoría Jurídica sobre un asunto. |

### Actos Administrativos y Normativos

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| ORD | Ordenanza | ALD | Norma de carácter general de mayor jerarquía municipal, aprobada por el Concejo. Encabezado "ORDENANZA". |
| ACC | Acuerdo de Concejo | CCM | Decisión del Concejo Municipal sobre asuntos de su competencia. |
| DAL | Decreto de Alcaldía | ALD | Resolución del Alcalde sobre asuntos administrativos de su cargo. Encabezado "DECRETO DE ALCALDÍA". |
| RAL | Resolución de Alcaldía | ALD | Acto administrativo del Alcalde que resuelve asuntos administrativos. Encabezado "RESOLUCIÓN DE ALCALDÍA". |
| RGM | Resolución de Gerencia Municipal | GRM | Acto administrativo del Gerente Municipal. |
| RGE | Resolución de Gerencia | GAF | Acto administrativo de un Gerente de línea. |

### TUPA — Procedimientos Administrativos al Ciudadano

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| LFN | Licencia de Funcionamiento | GDE | Autorización para el desarrollo de actividades económicas. |
| LED | Licencia de Edificación | GIT | Autorización para ejecutar obras de edificación. |
| LDM | Licencia de Demolición | GIT | Autorización para demoler una edificación. |
| LOM | Licencia de Obra Menor | GIT | Autorización para obras menores (cercos, refacciones). |
| HUR | Habilitación Urbana | GIT | Autorización para habilitar terrenos para uso urbano. |
| CPU | Certificado de Parámetros Urbanísticos y Edificación | GIT | Certifica los parámetros urbanísticos aplicables a un predio. |
| CZO | Certificado de Zonificación | GIT | Certifica la zonificación vigente de un predio. |
| CCU | Certificado de Compatibilidad de Uso | GIT | Certifica compatibilidad del uso del suelo. |
| CPO | Constancia de Posesión | GIT | Constancia de posesión de un predio. |
| CHB | Constancia de Habilidad | GIT | Constancia de habilidad de profesionales/constructores. |
| CNU | Certificado de Numeración | GIT | Asigna numeración oficial a un predio. |
| VPL | Visación de Planos | GIT | Visado de planos arquitectónicos/estructurales. |
| APO | Aprobación de Proyecto | GIT | Aprobación de proyecto arquitectónico/urbanización. |
| COB | Conformidad de Obra | GIT | Constata que la obra se ejecutó conforme al proyecto aprobado. |
| DFA | Declaratoria de Fábrica | GIT | Inscripción de la edificación en el registro de la propiedad. |
| AAN | Autorización de Anuncios | GAT | Autorización para colocar anuncios publicitarios. |
| AVP | Autorización de Uso de Vía Pública | GAT | Autorización para uso temporal de la vía pública. |
| PEV | Permiso de Evento Público | GSC | Permiso para desfiles, espectáculos, eventos en vía pública. |
| CNA | Constancia de No Adeudo | GAT | Constancia de no adeudo tributario municipal. |
| DJP | Declaración Jurada de Predio | GAT | Declaración jurada del autoavalúo del predio. |
| DJV | Declaración Jurada de Vehículo | GAT | Declaración jurada del autoavalúo vehicular. |

### Documentos Ciudadanos (mesa de partes / libro de reclamaciones)

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| SOL | Solicitud | OTD | Petición genérica del ciudadano ante la municipalidad. |
| DEN | Denuncia | GSC | Comunicación de un hecho presuntamente ilícito o infractor. |
| REC | Reclamo | OTD | Disconformidad del ciudadano con un servicio o acto municipal. |
| QUE | Queja | OCI | Queja contra un servidor público por mal desempeño. |
| SUG | Sugerencia | OTD | Propuesta o sugerencia ciudadana. |
| LIR | Hoja de Reclamaciones | OTD | Formato del libro de reclamaciones. |
| ACCS | Acceso a la Información Pública | OTD | Solicitud de información bajo la Ley 27806. |

### Documentos de Gobierno y Actas

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| ASC | Acta de Sesión de Concejo | CCM | Acta de la sesión del Concejo Municipal. |
| ACM | Acta de Comisión | CCM | Acta de una comisión regidoral. |
| ATR | Acta de Trabajo | GAF | Acta de reunión de trabajo interna. |

### Documentos Contractuales y Convenios

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| CON | Contrato | GAF | Contrato de locación de servicios, obra, suministro, etc. |
| CVN | Convenio | ALD | Convenio entre la municipalidad y otra entidad. |
| ADD | Adenda | GAF | Modificación a un contrato o convenio existente. |

### Documentos Financieros y de Control

| Código | Nombre | Área típica | Descripción para prompt LLM |
|--------|--------|-------------|-----------------------------|
| ORD2 | Orden de Pago/Compra/Servicio | GAF | Documento que ordena un pago o adquisición. |
| PECA | Pecosa | GLO | Parte de entrada y salida de almacén. |
| INF_AUD | Informe de Auditoría | OCI | Informe de control interno o auditoría. |
| INVC | Informe de Visitador | OCI | Informe de visita/inspección municipal. |

## Resumen del catálogo

- **Total áreas**: ~40 (incluyendo subgerencias y unidades especiales)
- **Total tipos documentales**: ~50
- Cobertura: gestión interna, actos administrativos, TUPA completo,
  documentos ciudadanos, actas, contratos y control.

## Notas de uso

- Los códigos son **sugeridos**; cada municipalidad puede reasignarlos.
- Los tipos marcados con `area_tipica` ayudan al LLM en su sugerencia,
  pero el operador puede mover cualquier documento a cualquier área.
- El sistema **precarga** este catálogo en `seed` al instalar; el admin
  puede editar, desactivar o añadir vía UI de Configuración.
- Este catálogo es **abarcador** pero **no cerrado**: está pensado para
  que cualquier municipalidad distrital del Perú encuentre su taxonomía
  reflejada o la ajuste con mínimo esfuerzo.
