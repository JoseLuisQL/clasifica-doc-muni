"""embeddings: reemplazar indice ivfflat por HNSW

El indice ivfflat original (lists=100) devuelve 0 resultados para consultas
semánticas reales cuando la tabla tiene pocos registros: ivfflat parte los
datos en 100 listas y, con probes=1 (default), solo explora la lista del
centroide mas cercano al vector de consulta. Con pocos vectores la mayoria
de listas estan vacias y el resultado se pierde → la búsqueda semántica no
devuelve nada (bug de US4 en datasets pequeños/reales).

HNSW no tiene ese problema: funciona correctamente a cualquier escala y no
requiere afinar lists/probes.

Revision ID: 0002_embeddings_hnsw
Revises: 0001_inicial
Create Date: 2026-07-08
"""
from alembic import op

revision = "0002_embeddings_hnsw"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector")
    op.execute(
        "CREATE INDEX idx_embeddings_vector ON documentos_embeddings "
        "USING hnsw (vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector")
    op.execute(
        "CREATE INDEX idx_embeddings_vector ON documentos_embeddings "
        "USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)"
    )
