"""
Celery tasks for webhook delivery and retry handling.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from celery import Task

from app.config import settings
from app.db.database import SyncSessionLocal
from app.models.delivery_log import DeliveryStatus
from app.services.delivery_service import SyncDeliveryService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class WebhookDeliveryTask(Task):
    """Base task class for webhook delivery with automatic retries."""
    
    max_retries = settings.MAX_RETRY_ATTEMPTS
    
    def get_retry_delay(self, attempt: int) -> int:
        """
        Get the retry delay for a specific attempt.
        
        Args:
            attempt: The attempt number (0-based index)
            
        Returns:
            Delay in seconds for this retry
        """
        retry_delays = settings.RETRY_DELAYS
        if attempt < len(retry_delays):
            return retry_delays[attempt]
        return retry_delays[-1]  # Use last value if we've gone beyond the list


@celery_app.task(name="app.workers.delivery_worker.process_webhook_delivery", bind=True, base=WebhookDeliveryTask)
def process_webhook_delivery(self, delivery_log_id: str) -> bool:
    """
    Process a webhook delivery.
    
    Args:
        delivery_log_id: UUID of the delivery log to process
        
    Returns:
        True if delivery was successful, False otherwise
    """
    session = SyncSessionLocal()
    try:
        delivery_service = SyncDeliveryService(session)
        log_id = UUID(delivery_log_id)
        
        # Get the delivery log
        log = delivery_service.get_delivery_log(log_id)
        if not log:
            logger.error(f"Delivery log {log_id} not found")
            return False
        
        logger.info(
            f"Processing webhook delivery: ID={log.id}, "
            f"Target={log.target_url}, Attempt={log.attempt_number}"
        )
        
        # Attempt to deliver the webhook
        success, http_status, error_details = delivery_service.deliver_webhook(log)
        
        # Update delivery log based on result
        if success:
            delivery_service.update_status(
                log_id=log.id,
                status=DeliveryStatus.SUCCESS,
                http_status=http_status
            )
            logger.info(f"Webhook delivery successful: ID={log.id}, HTTP Status={http_status}")
            return True
        else:
            # This was a failure - check if we should retry
            current_attempt = log.attempt_number
            should_retry = current_attempt < settings.MAX_RETRY_ATTEMPTS
            
            if should_retry:
                # Schedule a retry
                next_attempt = current_attempt
                retry_delay = self.get_retry_delay(next_attempt - 1)  # 0-based index
                next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                
                # Update the current log
                delivery_service.update_status(
                    log_id=log.id,
                    status=DeliveryStatus.FAILED_ATTEMPT,
                    http_status=http_status,
                    error_details=error_details
                )
                
                # Create a new log for the retry
                try:
                    retry_log = delivery_service.create_retry_log(
                        previous_log=log,
                        next_retry_at=next_retry_at
                    )
                    
                    if retry_log is None:
                        raise ValueError("Retry log creation returned None")
                        
                    logger.info(
                        f"Webhook delivery failed, retry scheduled: ID={log.id}, "
                        f"Next Attempt={retry_log.attempt_number}, Delay={retry_delay}s"
                    )
                    
                    # Schedule the retry task
                    process_webhook_delivery.apply_async(
                        args=[str(retry_log.id)],
                        countdown=retry_delay
                    )
                except Exception as retry_error:
                    # Handle any errors during retry creation
                    logger.error(f"Failed to create or schedule retry log: {str(retry_error)}")
                    # Update the current log to indicate retry failure
                    delivery_service.update_status(
                        log_id=log.id,
                        status=DeliveryStatus.FINAL_FAILURE,
                        http_status=http_status,
                        error_details=f"Failed to create retry log: {error_details}"
                    )
                    return False
            else:
                # No more retries - mark as final failure
                delivery_service.update_status(
                    log_id=log.id,
                    status=DeliveryStatus.FINAL_FAILURE,
                    http_status=http_status,
                    error_details=f"Maximum retry attempts ({settings.MAX_RETRY_ATTEMPTS}) exceeded. Last error: {error_details}"
                )
                logger.warning(
                    f"Webhook delivery failed, no more retries: ID={log.id}, "
                    f"Total Attempts={current_attempt}, Last Error={error_details}"
                )
            
            return False
    
    except Exception as e:
        logger.exception(f"Error processing webhook delivery {delivery_log_id}: {str(e)}")
        return False
    
    finally:
        session.close()