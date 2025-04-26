"""
Celery tasks for cleaning up old delivery logs.
"""
import logging

from celery import Task

from app.config import settings
from app.db.database import SyncSessionLocal
from app.services.delivery_service import DeliveryService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class LogCleanupTask(Task):
    """Base task class for log cleanup operations."""
    
    # For cleanup tasks, we don't want auto-retry behavior
    autoretry_for = ()
    retry_kwargs = {'max_retries': 0}
    ignore_result = True


@celery_app.task(name="app.workers.cleanup_worker.cleanup_old_logs", base=LogCleanupTask)
def cleanup_old_logs() -> int:
    """
    Scheduled task to clean up old delivery logs.
    
    Returns:
        Number of logs deleted
    """
    async def _run_cleanup():
        async with SyncSessionLocal() as session:
            service = DeliveryService(session)
            deleted_count = await service.clean_old_logs(hours=settings.LOG_RETENTION_HOURS)
            logger.info(f"Cleaned up {deleted_count} logs older than {settings.LOG_RETENTION_HOURS} hours")
            return deleted_count
    
    # Import here to avoid circular imports
    import asyncio
    return asyncio.run(_run_cleanup())