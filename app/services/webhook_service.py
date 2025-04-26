"""
Service for webhook-related business logic.
"""
import logging
import uuid
import traceback
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.delivery_log_repository import DeliveryLogRepository
from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.services.subscription_service import SubscriptionService
from app.utils.signature import verify_signature
from app.utils.sql_helpers import create_delivery_log_raw

# Setup logging
logger = logging.getLogger(__name__)

class WebhookService:
    """Service layer for webhook-related operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.subscription_service = SubscriptionService(session)
        self.delivery_log_repository = DeliveryLogRepository(session)
    
    async def process_webhook(
        self,
        subscription_id: UUID,
        payload: Dict[str, Any],
        event_type: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> Tuple[UUID, bool]:
        """
        Process a webhook for delivery.
        
        Args:
            subscription_id: Subscription UUID
            payload: Webhook payload
            event_type: Optional event type
            signature: Optional signature for verification
            
        Returns:
            Tuple of (webhook_id, is_accepted)
            
        Raises:
            HTTPException: If subscription not found, signature invalid, or event type not allowed
        """
        try:
            # Get the subscription
            subscription = await self.subscription_service.get_subscription(subscription_id)
            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")
            
            # Check if signature is valid (if subscription has a secret)
            if subscription.secret_key:
                is_valid = verify_signature(
                    payload=payload,
                    secret=subscription.secret_key,
                    signature=signature
                )
                if not is_valid:
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid signature"
                    )
            
            # Check if event type is allowed
            if event_type and subscription.event_types:
                is_allowed = await self.subscription_service.check_event_type_allowed(
                    subscription_id=subscription_id,
                    event_type=event_type
                )
                if not is_allowed:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Event type '{event_type}' not allowed for this subscription"
                    )
            
            # Generate a unique webhook ID
            webhook_id = uuid.uuid4()
            
            logger.info(f"Creating delivery log for webhook {webhook_id}")
            
            # Create a delivery log entry using raw SQL
            delivery_log_data = await create_delivery_log_raw(
                session=self.session,
                webhook_id=webhook_id,
                subscription_id=subscription_id,
                target_url=subscription.target_url,
                payload=payload,
                event_type=event_type,
                status=DeliveryStatus.PENDING
            )
            
            if not delivery_log_data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create delivery log"
                )
            
            logger.info(f"Queuing webhook {webhook_id} for delivery with log ID {delivery_log_data['id']}")
            
            # Queue the webhook for delivery - import here to avoid circular dependency
            try:
                from app.workers.celery_app import celery_app
                from app.config import settings
                
                task_name = "app.workers.delivery_worker.process_webhook_delivery"
                task_args = [str(delivery_log_data['id'])]
                
                # Use the appropriate method based on debug mode
                if settings.DEBUG and settings.ENVIRONMENT == "development":
                    # In debug mode, import and run the task directly
                    from app.workers.delivery_worker import process_webhook_delivery
                    process_webhook_delivery.delay(*task_args)
                else:
                    # In production mode, use send_task which works across processes
                    celery_app.send_task(
                        task_name,
                        args=task_args
                    )
                
                logger.info(f"Successfully queued webhook {webhook_id} for delivery")
            except Exception as e:
                logger.error(f"Failed to queue webhook {webhook_id}: {str(e)}")
                logger.error(traceback.format_exc())
                # Even if Celery fails, we return success since the webhook was accepted
            
            return webhook_id, True
        except HTTPException:
            # Pass through HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def get_webhook_status(self, webhook_id: UUID) -> Dict[str, Any]:
        """
        Get the status of a webhook delivery.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            Dictionary with webhook status details
            
        Raises:
            HTTPException: If webhook not found
        """
        try:
            logs = await self.delivery_log_repository.get_by_webhook_id(webhook_id)
            if not logs:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            # Get the latest attempt
            latest_log = max(logs, key=lambda l: l.attempt_number)
            
            # Count attempts by status
            statuses = {
                "total_attempts": len(logs),
                "successful": sum(1 for l in logs if l.status == DeliveryStatus.SUCCESS),
                "failed": sum(1 for l in logs if l.status == DeliveryStatus.FAILED_ATTEMPT),
                "pending": sum(1 for l in logs if l.status == DeliveryStatus.PENDING),
                "final_failure": sum(1 for l in logs if l.status == DeliveryStatus.FINAL_FAILURE)
            }
            
            # Format the response
            response = {
                "webhook_id": webhook_id,
                "subscription_id": latest_log.subscription_id,
                "event_type": latest_log.event_type,
                "status": latest_log.status.value if latest_log.status else None,  # Use .value to get string
                "created_at": latest_log.created_at,
                "updated_at": latest_log.updated_at,  # Add updated_at field
                "last_attempt_at": latest_log.updated_at,
                "next_retry_at": latest_log.next_retry_at,
                "target_url": latest_log.target_url,
                "payload": latest_log.payload,  # Add payload field
                "attempts": [
                    {
                        "attempt_number": log.attempt_number,
                        "status": log.status.value if log.status else None,  # Use .value to get string
                        "http_status": log.http_status,
                        "error_details": log.error_details,
                        "timestamp": log.updated_at
                    }
                    for log in sorted(logs, key=lambda l: l.attempt_number)
                ],
                "statistics": statuses
            }
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting webhook status: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")