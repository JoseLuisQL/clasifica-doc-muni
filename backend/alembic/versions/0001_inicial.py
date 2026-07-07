"""inicial: extensiones, tablas, indices

Revision ID: 0001_inicial
Revises:
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("nombre_completo", sa.String(), nullable=False),
        sa.Column("rol", sa.String(), nullable=False, server_default="admin"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "areas",
        sa.Column("codigo", sa.String(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("padre_codigo", sa.String(), sa.ForeignKey("areas.codigo"), nullable=True),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tipos_documentales",
        sa.Column("codigo", sa.String(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("area_tipica_codigo", sa.String(), sa.ForeignKey("areas.codigo"), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("palabras_clave", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("plantilla_correlativo", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hash_sha256", sa.String(), nullable=False, unique=True),
        sa.Column("correlativo", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente"),
        sa.Column("tipo_codigo", sa.String(), sa.ForeignKey("tipos_documentales.codigo"), nullable=True),
        sa.Column("area_codigo", sa.String(), sa.ForeignKey("areas.codigo"), nullable=True),
        sa.Column("asunto", sa.Text(), nullable=True),
        sa.Column("anio_documento", sa.Integer(), nullable=True),
        sa.Column("confianza", sa.Float(), nullable=True),
        sa.Column("justificacion_llm", sa.Text(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ruta_original", sa.Text(), nullable=False),
        sa.Column("ruta_clasificada", sa.Text(), nullable=True),
        sa.Column("num_paginas", sa.Integer(), nullable=True),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=False),
        sa.Column("origen", sa.String(), nullable=False, server_default="interactivo"),
        sa.Column("prioridad", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("cargado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version_config", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('spanish', coalesce(asunto,'')), 'A') || "
                "setweight(to_tsvector('spanish', coalesce(ocr_text,'')), 'B')",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index("idx_documentos_estado", "documentos", ["estado"])
    op.create_index("idx_documentos_correlativo", "documentos", ["correlativo"])
    op.create_index("idx_documentos_area_tipo_anio", "documentos", ["area_codigo", "tipo_codigo", "anio_documento"])
    op.create_index("idx_documentos_cargado_en", "documentos", [sa.text("cargado_en DESC")])
    op.create_index("idx_documentos_search", "documentos", ["search_vector"], postgresql_using="gin")
    op.create_index("idx_documentos_asunto_trgm", "documentos", ["asunto"], postgresql_using="gin", postgresql_ops={"asunto": "gin_trgm_ops"})

    op.create_table(
        "eventos_documento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("idx_eventos_doc", "eventos_documento", ["documento_id", sa.text("timestamp DESC")])

    op.create_table(
        "secuencias_correlativo",
        sa.Column("area_codigo", sa.String(), primary_key=True),
        sa.Column("anio", sa.Integer(), primary_key=True),
        sa.Column("tipo_codigo", sa.String(), primary_key=True),
        sa.Column("ultimo_valor", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "muestras_entrenamiento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_original", sa.String(), nullable=True),
        sa.Column("area_original", sa.String(), nullable=True),
        sa.Column("tipo_corregido", sa.String(), nullable=False),
        sa.Column("area_corregida", sa.String(), nullable=False),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("justificacion_operador", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("usada_en_reentrenamiento", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version_modelo", sa.String(), nullable=True),
    )

    op.create_table(
        "documentos_embeddings",
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documentos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("vector", Vector(384), nullable=False),
        sa.Column("modelo", sa.String(), nullable=False),
        sa.Column("generado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX idx_embeddings_vector ON documentos_embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)")

    op.create_table(
        "jobs_migracion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ruta_origen", sa.Text(), nullable=False),
        sa.Column("total_documentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("procesados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exitosos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("en_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erroneos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(), nullable=False, server_default="encolado"),
        sa.Column("iniciado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False),
    )
    op.create_index("idx_jobs_estado", "jobs_migracion", ["estado"])

    for tabla, pref in [("configuracion_correlativo", "corr"), ("configuracion_llm", "llm"), ("configuracion_anonimizacion", "anon")]:
        pass  # creadas abajo explícitamente

    op.create_table(
        "configuracion_correlativo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plantilla", sa.String(), nullable=False, server_default="{SEQ:04d}-{AREA}-{ANIO}-{TIPO}"),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_correlativo_singleton"),
    )
    op.create_table(
        "configuracion_llm",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("endpoint", sa.String(), nullable=False, server_default="https://api.qware.me/v1"),
        sa.Column("modelo", sa.String(), nullable=False, server_default="gemini-3-flash-agent"),
        sa.Column("api_key_secret_ref", sa.String(), nullable=False, server_default="LLM_API_KEY"),
        sa.Column("temperatura", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("timeout_segundos", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("modelo_embeddings", sa.String(), nullable=False, server_default="paraphrase-multilingual-MiniLM-L12-v2"),
        sa.Column("plantilla_system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_llm_singleton"),
    )
    op.create_table(
        "configuracion_anonimizacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patrones", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("redactar_firmas", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_anon_singleton"),
    )


def downgrade() -> None:
    for t in [
        "configuracion_anonimizacion", "configuracion_llm", "configuracion_correlativo",
        "jobs_migracion", "documentos_embeddings", "muestras_entrenamiento",
        "secuencias_correlativo", "eventos_documento", "documentos",
        "tipos_documentales", "areas", "usuarios",
    ]:
        op.drop_table(t)
