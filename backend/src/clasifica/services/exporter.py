"""Exportación de documentos a ZIP (PDFs) + CSV (metadatos)."""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path


def exportar_zip(documentos: list[dict]) -> bytes:
    """documentos: lista de dicts con metadatos + ruta_original/ruta_clasificada."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # CSV de metadatos
        csv_buf = io.StringIO()
        campos = [
            "correlativo", "tipo_codigo", "area_codigo", "asunto",
            "anio_documento", "confianza", "estado", "cargado_en", "ruta_clasificada",
        ]
        writer = csv.DictWriter(csv_buf, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        for d in documentos:
            writer.writerow({k: d.get(k, "") for k in campos})
        zf.writestr("metadatos.csv", csv_buf.getvalue())

        # PDFs
        for d in documentos:
            ruta = d.get("ruta_clasificada") or d.get("ruta_original")
            if ruta and Path(ruta).exists():
                nombre = (d.get("correlativo") or Path(ruta).stem) + ".pdf"
                zf.write(ruta, arcname=f"documentos/{nombre}")
    return buf.getvalue()
