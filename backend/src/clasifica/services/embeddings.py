"""Servicio de embeddings locales (sentence-transformers, on-premise).

Genera embeddings 384-dim del asunto+OCR para búsqueda semántica. El
modelo se carga una sola vez (singleton) y corre en CPU.
"""
from __future__ import annotations

import math
from functools import lru_cache

from clasifica.config import settings


@lru_cache(maxsize=1)
def _get_model():  # pragma: no cover - carga pesada, se testea con monkeypatch
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed_text(texto: str) -> list[float]:
    """Devuelve el embedding (lista de floats) del texto."""
    model = _get_model()
    vec = model.encode(texto or "", normalize_embeddings=True)
    return vec.tolist()


def embed_documento(asunto: str | None, ocr_text: str | None) -> list[float]:
    """Embedding combinado de asunto + primeros 4000 chars del OCR."""
    partes = [p for p in [(asunto or "").strip(), (ocr_text or "")[:4000].strip()] if p]
    return embed_text("\n".join(partes))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores (para tests / rankeo local)."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
