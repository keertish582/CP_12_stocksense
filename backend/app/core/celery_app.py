from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery = Celery(
    "stocksense_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DISPLAY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "nightly-demand-forecast-and-reorder": {
            "task": "app.tasks.celery_tasks.run_nightly_forecast_and_reorder",
            # Runs every night at 02:00 Asia/Kolkata
            "schedule": crontab(hour=2, minute=0),
        },
    },
)
