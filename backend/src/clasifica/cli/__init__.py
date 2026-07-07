"""CLI de mantenimiento y migración masiva."""
from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Uso: clasifica <comando> [args]\nComandos: migrate <carpeta>, jobs, seed")
        return
    cmd = args[0]
    if cmd == "seed":
        from clasifica.db.seeds.loader import main as seed_main

        seed_main()
    elif cmd == "migrate":
        if len(args) < 2:
            print("Uso: clasifica migrate <carpeta>")
            return
        _migrate(args[1])
    elif cmd == "jobs":
        _jobs_status()
    else:
        print(f"Comando desconocido: {cmd}")


def _migrate(carpeta: str) -> None:
    import uuid

    from clasifica.db.models import JobMigracion, Usuario
    from clasifica.workers.common import SyncSession
    from clasifica.workers.tasks.batch_migration import batch_migration

    with SyncSession() as session:
        admin = session.query(Usuario).filter_by(rol="admin").first()
        job = JobMigracion(ruta_origen=carpeta, operador_id=admin.id if admin else uuid.uuid4())
        session.add(job)
        session.commit()
        job_id = str(job.id)
    batch_migration.apply_async(args=[job_id], queue="batch")
    print(f"[migrate] Job {job_id} encolado para carpeta {carpeta}")


def _jobs_status() -> None:
    from clasifica.db.models import JobMigracion
    from clasifica.workers.common import SyncSession

    with SyncSession() as session:
        for j in session.query(JobMigracion).order_by(JobMigracion.iniciado_en.desc().nullslast()).limit(20):
            print(f"{j.id} | {j.estado} | {j.procesados}/{j.total_documentos} | ok={j.exitosos} rev={j.en_revision} err={j.erroneos}")


if __name__ == "__main__":
    main()
