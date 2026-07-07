"""Script de evaluación del clasificador (T096).

Corre la clasificación sobre PDFs de fixtures con ground truth conocido y
reporta precisión por tipo/área, matriz de confusión y latencias p50/p95.

Uso:
    python -m clasifica.eval_classifier tests/fixtures/pdfs tests/fixtures/expected_classifications.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path


def evaluar(carpeta: str, ground_truth_file: str) -> dict:
    import yaml

    from clasifica.db.seeds.loader import SEED_FILE
    from clasifica.services.classifier import clasificar_pdf

    catalogo = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8"))
    areas = [{"codigo": a["codigo"], "nombre": a["nombre"]} for a in catalogo["areas"]]
    tipos = [{"codigo": t["codigo"], "nombre": t["nombre"]} for t in catalogo["tipos"]]

    gt = json.loads(Path(ground_truth_file).read_text(encoding="utf-8"))
    aciertos_tipo = aciertos_area = total = 0
    latencias: list[float] = []
    confusion: dict[str, dict[str, int]] = {}

    for archivo, esperado in gt.items():
        pdf = Path(carpeta) / archivo
        if not pdf.exists():
            continue
        t0 = time.monotonic()
        res = clasificar_pdf(pdf.read_bytes(), areas=areas, tipos=tipos)
        latencias.append(time.monotonic() - t0)
        total += 1
        if res.llm.tipo_documento == esperado["tipo"]:
            aciertos_tipo += 1
        if res.llm.area == esperado["area"]:
            aciertos_area += 1
        confusion.setdefault(esperado["tipo"], {}).setdefault(res.llm.tipo_documento, 0)
        confusion[esperado["tipo"]][res.llm.tipo_documento] += 1

    return {
        "total": total,
        "precision_tipo": round(aciertos_tipo / total, 3) if total else 0,
        "precision_area": round(aciertos_area / total, 3) if total else 0,
        "latencia_p50": round(statistics.median(latencias), 2) if latencias else 0,
        "latencia_p95": round(sorted(latencias)[int(len(latencias) * 0.95)], 2) if len(latencias) > 1 else 0,
        "confusion": confusion,
    }


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python -m clasifica.eval_classifier <carpeta_pdfs> <ground_truth.json>")
        return
    resultado = evaluar(sys.argv[1], sys.argv[2])
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
