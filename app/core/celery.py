from celery import Celery
from app.core.config import settings

#redis_url = f"redis://:{settings.REDIS_PASSWORD}@localhost:{settings.REDIS_PORT}/0"
redis_url = settings.REDIS_URL


celery_app = Celery(
    "tasks", 
    broker=redis_url,
    backend=redis_url,
    include=['app.core.tasks']
    )


celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600, 
    timezone="UTC",
    enable_utc=True
)