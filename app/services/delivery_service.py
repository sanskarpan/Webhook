"""
Service for webhook delivery-related business logic.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.config import settings
from app.db.repositories.delivery_log_repository import DeliveryLogRepository
from app.models.delivery_log import DeliveryLog, DeliveryStatus


class DeliveryService:
    """Service layer for webhook delivery operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repository = DeliveryLogRepository(session)
    
    async def get_delivery_log(self, log_id: UUID) -> Optional[DeliveryLog]:
        """
        Get a delivery log by ID.
        
        Args:
            log_id: Delivery log UUID
            
        Returns:
            DeliveryLog if found, None otherwise
        """
        return await self.repository.get_by_id(log_id)
    
    async def get_delivery_attempts(
        self, subscription_id: UUID, limit: int = 20
    ) -> List[DeliveryLog]:
        """
        Get recent delivery attempts for a subscription.
        
        Args:
            subscription_id: Subscription UUID
            limit: Maximum number of logs to return
            
        Returns:
            List of recent DeliveryLog instances
        """
        return await self.repository.get_recent_by_subscription(
            subscription_id=subscription_id,
            limit=limit
        )
    
    async def get_delivery_statistics(
        self, subscription_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """
        Get delivery statistics.
        
        Args:
            subscription_id: Optional subscription UUID to filter by
            
        Returns:
            Dictionary with delivery statistics
        """
        status_counts = await self.repository.count_by_status(subscription_id)
        
        # Format the response
        statistics = {
            "total": sum(status_counts.values()),
            "successful": status_counts.get(DeliveryStatus.SUCCESS, 0),
            "failed": status_counts.get(DeliveryStatus.FAILED_ATTEMPT, 0),
            "pending": status_counts.get(DeliveryStatus.PENDING, 0),
            "final_failure": status_counts.get(DeliveryStatus.FINAL_FAILURE, 0)
        }
        
        return statistics
    
    async def clean_old_logs(self, hours: int = settings.LOG_RETENTION_HOURS) -> int:
        """
        Delete logs older than the specified time.
        
        Args:
            hours: Age in hours for logs to be deleted
            
        Returns:
            Number of deleted logs
        """
        threshold = datetime.utcnow() - timedelta(hours=hours)
        return await self.repository.clean_old_logs(older_than=threshold)


class SyncDeliveryService:
    """Synchronous version of the delivery service for use in Celery workers."""
    
    def __init__(self, session: Session):
        """
        Initialize the service with a synchronous database session.
        
        Args:
            session: SQLAlchemy sync session
        """
        self.session = session
    
    def get_delivery_log(self, log_id: UUID) -> Optional[DeliveryLog]:
        """
        Get a delivery log by ID (synchronous version).
        
        Args:
            log_id: Delivery log UUID
            
        Returns:
            DeliveryLog if found, None otherwise
        """
        return self.session.query(DeliveryLog).filter(DeliveryLog.id == log_id).first()
    
    def update_status(
        self,
        log_id: UUID,
        status: DeliveryStatus,
        http_status: Optional[int] = None,
        error_details: Optional[str] = None,
        next_retry_at: Optional[datetime] = None
    ) -> Optional[DeliveryLog]:
        """
        Update the status of a delivery log (synchronous version).
        
        Args:
            log_id: Delivery log UUID
            status: New status
            http_status: HTTP status code (if applicable)
            error_details: Error details (if applicable)
            next_retry_at: Next retry time (if applicable)
            
        Returns:
            Updated DeliveryLog instance or None if not found
        """
        log = self.get_delivery_log(log_id)
        if not log:
            return None
        
        log.status = status
        if http_status is not None:
            log.http_status = http_status
        if error_details is not None:
            log.error_details = error_details
        if next_retry_at is not None:
            log.next_retry_at = next_retry_at
        
        self.session.commit()
        return log
    
    def create_retry_log(
        self,
        previous_log: DeliveryLog,
        next_retry_at: Optional[datetime] = None
    ) -> DeliveryLog:
        """
        Create a new retry log entry (synchronous version).
        
        Args:
            previous_log: The previous failed delivery attempt
            next_retry_at: When to retry next
            
        Returns:
            New DeliveryLog instance for the retry
        """
        retry_log = DeliveryLog(
            webhook_id=previous_log.webhook_id,
            subscription_id=previous_log.subscription_id,
            target_url=previous_log.target_url,
            payload=previous_log.payload,
            event_type=previous_log.event_type,
            attempt_number=previous_log.attempt_number + 1,
            status=DeliveryStatus.PENDING,
            next_retry_at=next_retry_at
        )
        self.session.add(retry_log)
        self.session.commit()
        return retry_log
    
    def deliver_webhook(self, log: DeliveryLog) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Attempt to deliver a webhook.
        
        Args:
            log: DeliveryLog instance to deliver
            
        Returns:
            Tuple of (success, http_status_code, error_details)
        """
        try:
            # Send the webhook to the target URL
            with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT) as client:
                response = client.post(
                    url=log.target_url,
                    json=log.payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"{settings.APP_NAME}/1.0",
                        "X-Webhook-ID": str(log.webhook_id),
                        "X-Delivery-Attempt": str(log.attempt_number)
                    }
                )
                
                # Check if the request was successful (2xx status code)
                success = 200 <= response.status_code < 300
                return success, response.status_code, (
                    None if success else f"Target returned {response.status_code}: {response.text[:200]}"
                )
                
        except httpx.RequestError as e:
            # Handle connection errors, timeouts, etc.
            return False, None, f"Request error: {str(e)}"
        except Exception as e:
            # Handle any other unexpected errors
            return False, None, f"Unexpected error: {str(e)}"