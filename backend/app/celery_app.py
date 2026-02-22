from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "kreaimggen",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Retry / ack behaviour
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result expiry
    result_expires=3600,
    # Worker concurrency (override via env CELERYD_CONCURRENCY)
    worker_prefetch_multiplier=1,
    # Routing
    task_routes={
        "app.tasks.generate_image": {"queue": "image_generation"},
    },
    task_queues={
        "image_generation": {
            "exchange": "image_generation",
            "routing_key": "image_generation",
        }
    },
    # Flower events
    worker_send_task_events=True,
    task_send_sent_event=True,
)
