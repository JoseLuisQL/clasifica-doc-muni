# Quickstart — ClasificaDocMuni

**Branch**: `001-clasificacion-documentos-municipales` | **Date**: 2026-07-07

Cómo levantar el sistema en ~10 minutos sobre un servidor Linux.

## Prerrequisitos

- Docker 24+ y Docker Compose v2.
- 16GB RAM mínimo (32GB recomendado para migraciones grandes).
- 100GB disco libre.
- Conectividad saliente a la API LLM (OpenAI-compatible).
- Una API key válida para el proveedor LLM elegido.

## 1. Clonar y configurar

```bash
git clone <repo-url> clasifica-doc-muni
cd clasifica-doc-muni
cp infra/.env.example .env
```

Editar `.env`:

```env
# LLM (Qware, API OpenAI-compatible)
LLM_ENDPOINT=https://api.qware.me/v1
LLM_MODEL=gemini-3-flash-agent
LLM_API_KEY=sk-...                    # tu clave de Qware
LLM_RATE_LIMIT_RPM=50

# Embeddings locales (búsqueda semántica)
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384

# BD
POSTGRES_USER=clasifica
POSTGRES_PASSWORD=cambia-esta-clave
POSTGRES_DB=clasifica

# App
SECRET_KEY=genera-una-clave-larga-aleatoria
DATA_DIR=/var/clasifica/data          # ruta del host para volúmenes
ADMIN_USERNAME=admin
ADMIN_PASSWORD=cambia-esta-clave
```

## 2. Crear directorio de datos en el host

```bash
sudo mkdir -p /var/clasifica/data/{originales,documentos,tmp}
sudo chown -R 1000:1000 /var/clasifica       # uid del contenedor
```

## 3. Levantar

```bash
docker compose -f infra/docker-compose.yml up -d
# Migraciones Alembic se ejecutan automáticamente en el entrypoint del backend.
# Se crea el usuario admin inicial con las credenciales de .env.
```

Verificar:

```bash
docker compose ps
curl -f http://localhost:8080/health   # → {"status":"ok"}
```

## 4. Acceder

Abrir `http://<ip-servidor>:8080` en el navegador. Login con
`admin` / `cambia-esta-clave` (cambiar en primer ingreso).

## 5. Configurar taxonomía inicial

El sistema **precarga un catálogo TUPA base** (~40 áreas y ~50 tipos
documentales) según la Ley Orgánica de Municipalidades N° 27972. En
**Configuración → Áreas** y **Configuración → Tipos documentales**, el
operador revisa, activa/desactiva y ajusta lo que no aplique a su
municipalidad. No necesita crear desde cero.

## 6. Primer documento

- Ir a **Carga individual**, arrastrar un PDF.
- En ≤15s ver OCR + clasificación propuesta + correlativo.
- Confirmar o corregir campos → **Guardar**.
- Verificar en el explorador que el archivo quedó en
  `/2026/GDE/INF/0001-GDE-2026-INF-informe-...pdf`.

## 7. Migración masiva (opcional)

Vía UI: **Migración → Seleccionar carpeta → Subir**.

O vía CLI (para carpetas grandes en el servidor):

```bash
docker compose exec backend clasifica migrate /ruta/a/carpeta/historica
```

Monitorear progreso en **Migración → Jobs** o:

```bash
docker compose exec backend clasifica jobs status
```

## 8. Backups

```bash
# Diario vía cron (ejemplo en infra/scripts/backup.sh):
docker compose exec db pg_dump -U clasifica clasifica | gzip > /backup/db_$(date +%F).sql.gz
rsync -a /var/clasifica/data/ /backup/data/
```

## 9. Detener / actualizar

```bash
docker compose down                       # detener
docker compose pull && docker compose up -d  # actualizar
```

## Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Documentos encolados en "esperando LLM" | API key inválida o sin red | Verificar `LLM_API_KEY` y conectividad |
| OCR muy lento | PDFs pesados / sin preprocesamiento | Aumentar workers en `docker-compose.yml` |
| Error "sin texto extraíble" tras OCR | Calidad de escaneo muy baja | Revisar en bandeja; reintentar con preprocesamiento fuerte |
| Disco lleno | Hardlinks no soportados (copia) | Migrar `/var/clasifica/data` a ext4/xfs; revisar `/data/tmp` |
