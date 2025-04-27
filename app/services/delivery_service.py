"""
Service for webhook delivery-related business logic.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.db.repositories.delivery_log_repository import DeliveryLogRepository
from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.models.subscription import Subscription
from app.models.webhook import Webhook
from app.schemas.delivery import DeliveryStatusSummary
from app.utils.sql_helpers import create_delivery_log_raw, get_delivery_log_raw, update_delivery_log_status_raw, create_retry_log_raw, update_delivery_log_simple
from app.utils.signature import calculate_signature

logger = logging.getLogger(__name__)

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
    
    async def get_delivery_metrics(self, hours: int = 24) -> DeliveryStatusSummary:
        """
        Get delivery metrics for a specific time window.
        
        This method provides performance metrics for the webhook delivery system
        within the specified time window.
        
        Args:
            hours: Time window in hours (default: 24 hours)
            
        Returns:
            DeliveryStatusSummary object with aggregated metrics
        """
        # Calculate the time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Get statistics from the repository
        metrics = await self.repository.get_metrics_since(time_threshold)
        
        # Create and return the response model
        return DeliveryStatusSummary(
            total_attempts=metrics.get("total", 0),
            successful=metrics.get("successful", 0),
            failed=metrics.get("failed", 0),
            pending=metrics.get("pending", 0),
            final_failure=metrics.get("final_failure", 0)
        )
    
    async def update_status(
        self,
        log_id: UUID,
        status: DeliveryStatus,
        http_status: Optional[int] = None,
        error_details: Optional[str] = None,
        next_retry_at: Optional[datetime] = None
    ) -> Optional[DeliveryLog]:
        """
        Update the status of a delivery log.
        
        Args:
            log_id: Delivery log UUID
            status: New status
            http_status: HTTP status code (if applicable)
            error_details: Error details (if applicable)
            next_retry_at: Next retry time (if applicable)
            
        Returns:
            Updated DeliveryLog instance or None if not found
        """
        return await self.repository.update_status(
            log_id=log_id,
            status=status,
            http_status=http_status,
            error_details=error_details,
            next_retry_at=next_retry_at
        )
    
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

    async def create_retry_log(
        self,
        previous_log: DeliveryLog,
        next_retry_at: Optional[datetime] = None
    ) -> Optional[DeliveryLog]:
        """
        Create a new retry log entry.
        
        Args:
            previous_log: The previous failed delivery attempt
            next_retry_at: When to retry next
            
        Returns:
            New DeliveryLog instance for the retry
        """
        return await self.repository.create_retry_log(
            previous_log=previous_log,
            next_retry_at=next_retry_at
        )

    async def deliver_webhook(self, log: DeliveryLog) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Attempt to deliver a webhook.
        
        Args:
            log: DeliveryLog instance to deliver
            
        Returns:
            Tuple of (success, http_status_code, error_details)
        """
        try:
            # Get the subscription for the secret key
            subscription = await self.get_subscription(log.subscription_id)
            if not subscription:
                return False, None, "Subscription not found"
            
            # Calculate HMAC signature for payload
            signature = calculate_signature(log.payload, subscription.secret_key)
            
            # Send the webhook to the target URL
            with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT) as client:
                response = client.post(
                    url=log.target_url,
                    json=log.payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"{settings.APP_NAME}/1.0",
                        "X-Webhook-ID": str(log.webhook_id),
                        "X-Delivery-Attempt": str(log.attempt_number),
                        "X-Hub-Signature-256": signature
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

class SyncDeliveryService:
    """Service for webhook delivery operations using synchronous SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    def get_webhook(self, webhook_id: UUID) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self.session.get(Webhook, webhook_id)

    def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get a subscription by ID."""
        return self.session.get(Subscription, subscription_id)

    def get_delivery_log(self, delivery_log_id: UUID) -> Optional[DeliveryLog]:
        """
        Get a delivery log by ID using raw SQL to avoid enum issues.
        
        Args:
            delivery_log_id: The UUID of the delivery log
            
        Returns:
            DeliveryLog object or None if not found
        """
        try:
            # Use the raw SQL helper to get the log data
            log_data = get_delivery_log_raw(self.session, delivery_log_id)
            
            if not log_data:
                return None
                
            # Convert dict to DeliveryLog object
            log = DeliveryLog()
            log.id = log_data["id"]
            log.webhook_id = log_data["webhook_id"]
            log.subscription_id = log_data["subscription_id"]
            log.target_url = log_data["target_url"]
            log.payload = log_data["payload"]
            log.event_type = log_data["event_type"]
            log.attempt_number = log_data["attempt_number"]
            log.status = log_data["status"]
            log.http_status = log_data["http_status"]
            log.error_details = log_data["error_details"]
            log.created_at = log_data["created_at"]
            log.updated_at = log_data["updated_at"]
            log.next_retry_at = log_data["next_retry_at"]
            
            return log
        except Exception as e:
            logger.error(f"Error getting delivery log: {str(e)}")
            return None
    
    def get_delivery_logs_for_webhook(
        self, webhook_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[DeliveryLog]:
        """Get delivery logs for a webhook."""
        query = (
            select(DeliveryLog)
            .where(DeliveryLog.webhook_id == webhook_id)
            .order_by(DeliveryLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(query).scalars())

    def get_delivery_logs_for_subscription(
        self, subscription_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[DeliveryLog]:
        """Get delivery logs for a subscription."""
        query = (
            select(DeliveryLog)
            .where(DeliveryLog.subscription_id == subscription_id)
            .order_by(DeliveryLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(query).scalars())
            
    def update_delivery_log_with_result(
        self,
        delivery_log_id: UUID,
        status: DeliveryStatus,
        http_status: Optional[int] = None,
        error_details: Optional[str] = None,
        next_retry_at: Optional[datetime] = None,
    ) -> Optional[DeliveryLog]:
        """Update a delivery log with delivery result."""
        try:
            # Convert the enum value to string for the raw SQL function
            status_str = status.value if hasattr(status, 'value') else str(status)
            
            # Use the raw SQL helper function to update the status
            log_data = update_delivery_log_simple(
                self.session,
                delivery_log_id,
                status_str,
                http_status,
                error_details,
                next_retry_at
            )
            
            if not log_data:
                return None
                
            # Convert dict to DeliveryLog object
            log = DeliveryLog()
            log.id = log_data["id"]
            log.webhook_id = log_data["webhook_id"]
            log.subscription_id = log_data["subscription_id"]
            log.target_url = log_data["target_url"]
            log.payload = log_data["payload"]
            log.event_type = log_data["event_type"]
            log.attempt_number = log_data["attempt_number"]
            log.status = log_data["status"]
            log.http_status = log_data["http_status"]
            log.error_details = log_data["error_details"]
            log.created_at = log_data["created_at"]
            log.updated_at = log_data["updated_at"]
            log.next_retry_at = log_data["next_retry_at"]
            
            return log
            
        except Exception as e:
            logger.error(f"Error updating delivery log result: {str(e)}")
            return None

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
        try:
            # Convert the enum value to string for the raw SQL function
            status_str = status.value if hasattr(status, 'value') else str(status)
            
            # Use the simplified direct SQL helper instead
            log_data = update_delivery_log_simple(
                self.session,
                log_id,
                status_str,
                http_status,
                error_details,
                next_retry_at
            )
            
            if not log_data:
                return None
                
            # Convert dict to DeliveryLog object
            log = DeliveryLog()
            log.id = log_data["id"]
            log.webhook_id = log_data["webhook_id"]
            log.subscription_id = log_data["subscription_id"]
            log.target_url = log_data["target_url"]
            log.payload = log_data["payload"]
            log.event_type = log_data["event_type"]
            log.attempt_number = log_data["attempt_number"]
            log.status = log_data["status"]
            log.http_status = log_data["http_status"]
            log.error_details = log_data["error_details"]
            log.created_at = log_data["created_at"]
            log.updated_at = log_data["updated_at"]
            log.next_retry_at = log_data["next_retry_at"]
            
            return log
            
        except Exception as e:
            logger.error(f"Error updating delivery log status: {str(e)}")
            return None
    
    def create_retry_log(
        self,
        previous_log: DeliveryLog,
        next_retry_at: Optional[datetime] = None
    ) -> Optional[DeliveryLog]:
        """
        Create a new retry log entry (synchronous version).
        
        Args:
            previous_log: The previous failed delivery attempt
            next_retry_at: When to retry next
            
        Returns:
            New DeliveryLog instance for the retry or None on error
        """
        try:
            # Convert the previous log to a dictionary format for the raw SQL helper
            previous_log_data = {
                "webhook_id": previous_log.webhook_id,
                "subscription_id": previous_log.subscription_id,
                "target_url": previous_log.target_url,
                "payload": previous_log.payload,
                "event_type": previous_log.event_type,
                "attempt_number": previous_log.attempt_number,
            }
            
            # Use the raw SQL helper function to create the retry log
            log_data = create_retry_log_raw(
                self.session,
                previous_log_data,
                next_retry_at
            )
            
            if not log_data:
                return None
                
            # Convert dict to DeliveryLog object
            log = DeliveryLog()
            log.id = log_data["id"]
            log.webhook_id = log_data["webhook_id"]
            log.subscription_id = log_data["subscription_id"]
            log.target_url = log_data["target_url"]
            log.payload = log_data["payload"]
            log.event_type = log_data["event_type"]
            log.attempt_number = log_data["attempt_number"]
            log.status = log_data["status"]
            log.http_status = log_data["http_status"]
            log.error_details = log_data["error_details"]
            log.created_at = log_data["created_at"]
            log.updated_at = log_data["updated_at"]
            log.next_retry_at = log_data["next_retry_at"]
            
            return log
            
        except Exception as e:
            logger.error(f"Error creating retry log: {str(e)}")
            return None
    
    def deliver_webhook(self, log: DeliveryLog) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Attempt to deliver a webhook.
        
        Args:
            log: DeliveryLog instance to deliver
            
        Returns:
            Tuple of (success, http_status_code, error_details)
        """
        try:
            # Get the subscription for the secret key
            subscription = self.get_subscription(log.subscription_id)
            if not subscription:
                return False, None, "Subscription not found"
            
            # Calculate HMAC signature for payload
            signature = calculate_signature(log.payload, subscription.secret_key)
            
            # Send the webhook to the target URL
            with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT) as client:
                response = client.post(
                    url=log.target_url,
                    json=log.payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"{settings.APP_NAME}/1.0",
                        "X-Webhook-ID": str(log.webhook_id),
                        "X-Delivery-Attempt": str(log.attempt_number),
                        "X-Hub-Signature-256": signature
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