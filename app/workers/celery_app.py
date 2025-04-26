"""
Celery configuration and application setup.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "webhook_delivery_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.delivery_worker",
        "app.workers.cleanup_worker",
    ],
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    task_track_started=True,
    
    # Connection settings
    broker_connection_retry=True,  # Retry if connection fails
    broker_connection_retry_on_startup=True,  # Explicitly set retry behavior on startup
    
    # Concurrency settings
    worker_concurrency=4,  # Adjust based on your server resources
    
    # Queue settings
    task_default_queue="default",
    task_create_missing_queues=True,
    
    # Retry settings
    task_acks_late=True,  # Tasks are acknowledged after execution
    task_reject_on_worker_lost=True,  # Requeue tasks if worker is killed
    
    # Result settings
    task_ignore_result=False,  # We need task results for status tracking
    result_expires=60 * 60 * 72,  # 72 hours (matching log retention)
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-logs": {
            "task": "app.workers.cleanup_worker.cleanup_old_logs",
            "schedule": crontab(minute=0, hour="*/1"),  # Run every hour
            "options": {"expires": 60 * 5},  # Expire task after 5 minutes if not run
        },
    },
)

# If in development mode, enable task debugging
if settings.ENVIRONMENT == "development":
    celery_app.conf.update(
        task_always_eager=settings.DEBUG,  # Run tasks synchronously in debug mode
        task_eager_propagates=True,  # Propagate exceptions in eager mode
        broker_url='memory://' if settings.DEBUG else settings.CELERY_BROKER_URL,
        result_backend='memory://' if settings.DEBUG else settings.CELERY_RESULT_BACKEND,
    )


@celery_app.task(bind=True)
def debug_task(self):
    """
    Debug task to verify Celery is working correctly.
    """
    print(f"Request: {self.request!r}")
    return {"status": "Celery is working!"}