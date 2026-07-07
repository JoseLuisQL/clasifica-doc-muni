"""Jerarquía de excepciones del dominio."""


class ClasificaError(Exception):
    """Base de todos los errores del sistema."""


class DocumentoInvalido(ClasificaError):
    """PDF corrupto, vacío o no procesable."""


class TaxonomiaError(ClasificaError):
    """Área o tipo fuera de la taxonomía vigente."""


class LLMNoDisponible(ClasificaError):
    """La API del LLM no responde; el documento debe encolarse para reintento."""
