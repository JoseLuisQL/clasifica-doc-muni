"""OCR y detección de texto nativo en PDFs.

- Si el PDF ya tiene texto extraíble (pdfplumber), se usa directo.
- Si no, se rasteriza la primera página y se aplica OCR (PaddleOCR español).
- PaddleOCR y OpenCV son dependencias opcionales (extra "ocr"); se importan
  perezosamente para permitir tests sin ellas.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass


@dataclass
class ResultadoOCR:
    texto: str
    num_paginas: int
    es_nativo: bool
    primera_pagina_png_b64: str | None = None


def _texto_nativo(pdf_bytes: bytes) -> tuple[str, int]:
    import pdfplumber

    textos: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        n = len(pdf.pages)
        for page in pdf.pages:
            textos.append(page.extract_text() or "")
    return "\n".join(textos).strip(), n


def _render_primera_pagina_png(pdf_bytes: bytes) -> bytes:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_bytes)
    page = doc[0]
    bitmap = page.render(scale=2.0)
    pil = bitmap.to_pil()
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()


def _ocr_imagen(png_bytes: bytes) -> str:  # pragma: no cover - requiere paddle
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
    import numpy as np
    from PIL import Image

    img = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
    result = ocr.ocr(img, cls=True)
    lineas: list[str] = []
    for bloque in result or []:
        for _, (txt, _conf) in bloque or []:
            lineas.append(txt)
    return "\n".join(lineas).strip()


def procesar_pdf(pdf_bytes: bytes, min_chars_nativo: int = 40) -> ResultadoOCR:
    """Extrae texto de un PDF: nativo si hay, OCR si es escaneado."""
    texto, n = _texto_nativo(pdf_bytes)
    png_b64: str | None = None
    try:
        png = _render_primera_pagina_png(pdf_bytes)
        png_b64 = base64.b64encode(png).decode("ascii")
    except Exception:  # noqa: BLE001 - render best-effort
        png = None

    if len(texto) >= min_chars_nativo:
        return ResultadoOCR(texto=texto, num_paginas=n, es_nativo=True, primera_pagina_png_b64=png_b64)

    # Escaneado: OCR sobre la primera página renderizada
    ocr_txt = ""
    if png is not None:
        try:
            ocr_txt = _ocr_imagen(png)
        except Exception:  # noqa: BLE001 - OCR opcional
            ocr_txt = texto
    return ResultadoOCR(
        texto=ocr_txt or texto, num_paginas=n, es_nativo=False, primera_pagina_png_b64=png_b64
    )
