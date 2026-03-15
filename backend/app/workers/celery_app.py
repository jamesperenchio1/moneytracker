from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "moneytracker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Bangkok",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "update-asset-prices": {
        "task": "app.workers.tasks.update_all_asset_prices",
        "schedule": crontab(minute="*/15", hour="9-17", day_of_week="1-5"),  # Every 15min during market hours
    },
    "fetch-historical-prices-daily": {
        "task": "app.workers.tasks.fetch_missing_historical_prices",
        "schedule": crontab(hour=18, minute=0),  # Daily at 6pm
    },
}
