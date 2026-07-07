"""Anonimización de PII antes de enviar contenido al LLM externo.

Redacta DNI, RUC, teléfonos, emails (regex configurable) y registra qué
patrones se anonimizaron (para auditoría, sin guardar el valor original).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Patrones por defecto (Perú). Configurable vía ConfiguracionAnonimizacion.
DEFAULT_PATRONES: list[dict] = [
    {"nombre": "DNI", "regex": r"\b\d{8}\b", "reemplazo": "[DNI]"},
    {"nombre": "RUC", "regex": r"\b\d{11}\b", "reemplazo": "[RUC]"},
    {"nombre": "TEL", "regex": r"\b9\d{8}\b", "reemplazo": "[TEL]"},
    {"nombre": "EMAIL", "regex": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "reemplazo": "[EMAIL]"},
]


@dataclass
class ResultadoAnonimizacion:
    texto: str
    patrones_aplicados: dict[str, int] = field(default_factory=dict)


def anonimizar_texto(texto: str, patrones: list[dict] | None = None) -> ResultadoAnonimizacion:
    """Aplica los patrones sobre el texto. RUC (11) antes que DNI (8) para no cortar."""
    if not texto:
        return ResultadoAnonimizacion(texto="")
    patrones = patrones or DEFAULT_PATRONES
    # Ordenar por longitud de match descendente evita que \d{8} coma parte de \d{11}
    ordenados = sorted(patrones, key=lambda p: p.get("nombre") != "RUC")
    conteo: dict[str, int] = {}
    out = texto
    for p in ordenados:
        nombre = p["nombre"]
        reemplazo = p.get("reemplazo", f"[{nombre}]")
        out, n = re.subn(p["regex"], reemplazo, out)
        if n:
            conteo[nombre] = conteo.get(nombre, 0) + n
    return ResultadoAnonimizacion(texto=out, patrones_aplicados=conteo)
