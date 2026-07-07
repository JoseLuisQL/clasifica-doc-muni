"""Deduplicación por hash SHA-256."""
import hashlib
from pathlib import Path


def hash_bytes(data: bytes) -> str:
    """SHA-256 hex de un contenido en bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str | Path) -> str:
    """SHA-256 hex de un archivo, leyendo por bloques."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
