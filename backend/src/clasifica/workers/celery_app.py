"""Celery app: colas interactive / batch / retry."""
from celery import Celery

from clasifica.config import settings

celery_app = Celery(
    "clasifica",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_default_queue="interactive",
    task_routes={
        "clasifica.process_document": {"queue": "interactive"},
        "clasifica.batch_migration": {"queue": "batch"},
        "clasifica.retry_failed": {"queue": "retry"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_track_started=True,
    result_expires=3600,
)

# Registrar tareas
from clasifica.workers.tasks import batch_migration, process_document  # noqa: E402,F401
