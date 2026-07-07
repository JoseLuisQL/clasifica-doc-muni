"""Loader del seed inicial: catálogo TUPA + configuraciones singleton + admin.

Se ejecuta en el entrypoint (idempotente: no duplica si ya existe).
Usa SQLAlchemy síncrono para simplicidad en el arranque.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from clasifica.config import settings
from clasifica.core.security import hash_password
from clasifica.db.models import (
    Area,
    ConfiguracionAnonimizacion,
    ConfiguracionCorrelativo,
    ConfiguracionLLM,
    TipoDocumental,
    Usuario,
)
from clasifica.services.anonymize import DEFAULT_PATRONES
from clasifica.services.llm_client import DEFAULT_SYSTEM_PROMPT

SEED_FILE = Path(__file__).parent / "tupa_base.yaml"


def cargar_catalogo(session: Session) -> None:
    data = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8"))
    # Áreas: primero las que no tienen padre (o cualquier orden; FK admite null)
    for a in sorted(data["areas"], key=lambda x: x["orden"]):
        if session.get(Area, a["codigo"]):
            continue
        session.add(
            Area(
                codigo=a["codigo"],
                nombre=a["nombre"],
                padre_codigo=a.get("padre"),
                tipo=a.get("tipo"),
                orden=a.get("orden", 0),
            )
        )
    session.flush()
    for t in data["tipos"]:
        if session.get(TipoDocumental, t["codigo"]):
            continue
        session.add(
            TipoDocumental(
                codigo=t["codigo"],
                nombre=t["nombre"],
                area_tipica_codigo=t.get("area_tipica"),
                descripcion=t.get("descripcion"),
                palabras_clave=t.get("palabras_clave", []),
            )
        )


def cargar_configuraciones(session: Session) -> None:
    if not session.get(ConfiguracionCorrelativo, 1):
        session.add(ConfiguracionCorrelativo(id=1, plantilla="{SEQ:04d}-{AREA}-{ANIO}-{TIPO}"))
    if not session.get(ConfiguracionLLM, 1):
        session.add(
            ConfiguracionLLM(
                id=1,
                endpoint=settings.llm_endpoint,
                modelo=settings.llm_model,
                api_key_secret_ref="LLM_API_KEY",
                modelo_embeddings=settings.embedding_model,
                plantilla_system_prompt=DEFAULT_SYSTEM_PROMPT,
            )
        )
    if not session.get(ConfiguracionAnonimizacion, 1):
        session.add(ConfiguracionAnonimizacion(id=1, patrones=DEFAULT_PATRONES, redactar_firmas=True))


def crear_admin(session: Session) -> None:
    existe = session.execute(
        select(Usuario).where(Usuario.username == settings.admin_username)
    ).scalar_one_or_none()
    if not existe:
        session.add(
            Usuario(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                nombre_completo="Administrador",
                rol="admin",
            )
        )


def main() -> None:
    engine = create_engine(settings.sync_database_url.replace("psycopg2", "psycopg"), future=True)
    with Session(engine) as session:
        cargar_catalogo(session)
        cargar_configuraciones(session)
        crear_admin(session)
        session.commit()
    print("[seed] Catálogo TUPA, configuraciones y admin cargados.")


if __name__ == "__main__":
    main()
