"""Organización física de archivos: almacén inmutable + hardlinks clasificados.

- Original: {DATA_DIR}/originales/AB/CD/<hash>.pdf  (inmutable, hash sharded)
- Clasificado: {DATA_DIR}/documentos/{AÑO}/{AREA}/{TIPO}/{CORRELATIVO}-{slug}.pdf
  (hardlink al original; copia si el FS no soporta hardlink cross-device)
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from clasifica.config import settings
from clasifica.services.correlativo import slugify_asunto


def _data_dir() -> Path:
    return Path(settings.data_dir)


def ruta_original(hash_sha256: str) -> Path:
    return _data_dir() / "originales" / hash_sha256[:2] / hash_sha256[2:4] / f"{hash_sha256}.pdf"


def guardar_original(pdf_bytes: bytes, hash_sha256: str) -> Path:
    """Guarda el PDF en el almacén inmutable (idempotente por hash)."""
    dest = ruta_original(hash_sha256)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(pdf_bytes)
    return dest


def ruta_clasificada(anio: int, area: str, tipo: str, correlativo: str, asunto: str | None) -> Path:
    slug = slugify_asunto(asunto)
    return (
        _data_dir() / "documentos" / str(anio) / area / tipo / f"{correlativo}-{slug}.pdf"
    )


def ubicar_clasificado(
    hash_sha256: str, *, anio: int, area: str, tipo: str, correlativo: str, asunto: str | None
) -> Path:
    """Crea el hardlink (o copia) del original en la ruta clasificada."""
    origen = ruta_original(hash_sha256)
    dest = ruta_clasificada(anio, area, tipo, correlativo, asunto)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(origen, dest)
    except OSError:
        shutil.copy2(origen, dest)
    return dest


def reubicar(vieja: str | None, *, hash_sha256: str, anio: int, area: str, tipo: str, correlativo: str, asunto: str | None) -> Path:
    """Elimina el hardlink viejo y crea el nuevo (al corregir clasificación)."""
    if vieja:
        import contextlib

        with contextlib.suppress(OSError):
            Path(vieja).unlink(missing_ok=True)
    return ubicar_clasificado(
        hash_sha256, anio=anio, area=area, tipo=tipo, correlativo=correlativo, asunto=asunto
    )
