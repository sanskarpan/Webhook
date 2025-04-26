"""
Repository for delivery log-related database operations.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.utils.sql_helpers import get_delivery_log_raw


class DeliveryLogRepository:
    """Repository for delivery log-related database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(
        self,
        webhook_id: UUID,
        subscription_id: UUID,
        target_url: str,
        payload: Dict[str, Any],
        event_type: Optional[str] = None
    ) -> DeliveryLog:
        """
        Create a new delivery log entry.
        
        Args:
            webhook_id: Unique ID for this webhook delivery
            subscription_id: Subscription ID
            target_url: Target URL for the webhook
            payload: JSON payload to deliver
            event_type: Optional event type
            
        Returns:
            Created DeliveryLog instance
        """
        # Create the delivery log without committing
        delivery_log = DeliveryLog(
            webhook_id=webhook_id,
            subscription_id=subscription_id,
            target_url=target_url,
            payload=payload,
            event_type=event_type,
            status=DeliveryStatus.PENDING,  # Use the enum directly
            attempt_number=1
        )
        
        # Add it to the session
        self.session.add(delivery_log)
        
        try:
            # Commit the session
            await self.session.commit()
            # Refresh the instance to get generated values
            await self.session.refresh(delivery_log)
            return delivery_log
        except Exception as e:
            # Roll back in case of error
            await self.session.rollback()
            # Re-raise the exception
            raise e
    
    async def get_by_id(self, log_id: UUID) -> Optional[DeliveryLog]:
        """
        Get a delivery log by ID.
        
        Args:
            log_id: Delivery log UUID
            
        Returns:
            DeliveryLog if found, None otherwise
        """
        query = select(DeliveryLog).where(DeliveryLog.id == log_id)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_by_webhook_id(self, webhook_id: UUID) -> List[DeliveryLog]:
        """
        Get all delivery logs for a specific webhook.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            List of DeliveryLog instances for the webhook
        """
        # Use raw SQL to avoid enum issues
        query = text("""
            SELECT 
                id, webhook_id, subscription_id, target_url, payload, 
                event_type, attempt_number, status, http_status, error_details, 
                created_at, updated_at, next_retry_at
            FROM delivery_logs
            WHERE webhook_id = :webhook_id
            ORDER BY attempt_number
        """)
        
        result = await self.session.execute(query, {"webhook_id": webhook_id})
        rows = result.fetchall()
        
        if not rows:
            return []
            
        logs = []
        for row in rows:
            # Convert row to dict
            row_dict = dict(row._mapping)
            
            # Create DeliveryLog object
            log = DeliveryLog()
            log.id = row_dict["id"]
            log.webhook_id = row_dict["webhook_id"]
            log.subscription_id = row_dict["subscription_id"]
            log.target_url = row_dict["target_url"]
            log.payload = row_dict["payload"]
            log.event_type = row_dict["event_type"]
            log.attempt_number = row_dict["attempt_number"]
            
            # Handle enum conversion
            status_str = row_dict["status"]
            for enum_val in DeliveryStatus:
                if enum_val.value == status_str:
                    log.status = enum_val
                    break
            
            log.http_status = row_dict["http_status"]
            log.error_details = row_dict["error_details"]
            log.created_at = row_dict["created_at"]
            log.updated_at = row_dict["updated_at"]
            log.next_retry_at = row_dict["next_retry_at"]
            
            logs.append(log)
            
        return logs
    
    async def get_recent_by_subscription(
        self, subscription_id: UUID, limit: int = 20
    ) -> List[DeliveryLog]:
        """
        Get recent delivery logs for a subscription.
        
        Args:
            subscription_id: Subscription UUID
            limit: Maximum number of logs to return
            
        Returns:
            List of recent DeliveryLog instances
        """
        # Use raw SQL to avoid enum issues
        query = text("""
            SELECT 
                id, webhook_id, subscription_id, target_url, payload, 
                event_type, attempt_number, status, http_status, error_details, 
                created_at, updated_at, next_retry_at
            FROM delivery_logs
            WHERE subscription_id = :subscription_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        result = await self.session.execute(query, {
            "subscription_id": subscription_id,
            "limit": limit
        })
        rows = result.fetchall()
        
        if not rows:
            return []
            
        logs = []
        for row in rows:
            # Convert row to dict
            row_dict = dict(row._mapping)
            
            # Create DeliveryLog object
            log = DeliveryLog()
            log.id = row_dict["id"]
            log.webhook_id = row_dict["webhook_id"]
            log.subscription_id = row_dict["subscription_id"]
            log.target_url = row_dict["target_url"]
            log.payload = row_dict["payload"]
            log.event_type = row_dict["event_type"]
            log.attempt_number = row_dict["attempt_number"]
            
            # Handle enum conversion
            status_str = row_dict["status"]
            for enum_val in DeliveryStatus:
                if enum_val.value == status_str:
                    log.status = enum_val
                    break
            
            log.http_status = row_dict["http_status"]
            log.error_details = row_dict["error_details"]
            log.created_at = row_dict["created_at"]
            log.updated_at = row_dict["updated_at"]
            log.next_retry_at = row_dict["next_retry_at"]
            
            logs.append(log)
            
        return logs
    
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
        log = await self.get_by_id(log_id)
        if not log:
            return None
        
        log.status = status
        if http_status is not None:
            log.http_status = http_status
        if error_details is not None:
            log.error_details = error_details
        if next_retry_at is not None:
            log.next_retry_at = next_retry_at
        
        try:
            await self.session.commit()
            await self.session.refresh(log)
            return log
        except Exception as e:
            await self.session.rollback()
            raise e
    
    async def create_retry_log(
        self,
        previous_log: DeliveryLog,
        next_retry_at: Optional[datetime] = None
    ) -> DeliveryLog:
        """
        Create a new retry log entry based on a previous delivery log.
        
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
        
        try:
            await self.session.commit()
            await self.session.refresh(retry_log)
            return retry_log
        except Exception as e:
            await self.session.rollback()
            raise e
    
    async def get_due_for_delivery(self, limit: int = 100) -> List[DeliveryLog]:
        """
        Get logs due for delivery or retry.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of logs due for delivery/retry
        """
        now = datetime.utcnow()
        query = (
            select(DeliveryLog)
            .where(
                and_(
                    DeliveryLog.status == DeliveryStatus.PENDING,
                    or_(
                        DeliveryLog.next_retry_at.is_(None),
                        DeliveryLog.next_retry_at <= now
                    )
                )
            )
            .order_by(DeliveryLog.created_at)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_by_status(
        self, subscription_id: Optional[UUID] = None
    ) -> Dict[DeliveryStatus, int]:
        """
        Count delivery logs by status.
        
        Args:
            subscription_id: Optional subscription UUID to filter by
            
        Returns:
            Dictionary mapping status to count
        """
        query = select(DeliveryLog.status, func.count()).group_by(DeliveryLog.status)
        
        if subscription_id:
            query = query.where(DeliveryLog.subscription_id == subscription_id)
        
        result = await self.session.execute(query)
        return {status: count for status, count in result.all()}
    
    async def clean_old_logs(self, older_than: datetime) -> int:
        """
        Delete logs older than the specified time.
        
        Args:
            older_than: Datetime threshold for deletion
            
        Returns:
            Number of deleted logs
        """
        query = delete(DeliveryLog).where(DeliveryLog.created_at < older_than)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount
    
    async def get_metrics_since(self, since: datetime) -> Dict[str, int]:
        """
        Get metrics for delivery logs since a specific timestamp.
        
        Args:
            since: Start timestamp for metrics calculation
            
        Returns:
            Dictionary with metrics including counts by status
        """
        # Use SQL to get counts by status
        query = text("""
            SELECT 
                status, 
                COUNT(*) as count
            FROM 
                delivery_logs
            WHERE 
                created_at >= :since
            GROUP BY 
                status
        """)
        
        result = await self.session.execute(query, {"since": since})
        rows = result.fetchall()
        
        # Initialize metrics with zeroes
        metrics = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "pending": 0,
            "final_failure": 0
        }
        
        # Process result rows
        for row in rows:
            status = row._mapping["status"]
            count = row._mapping["count"]
            metrics["total"] += count
            
            # Map database status to metrics keys
            if status == DeliveryStatus.SUCCESS.value:
                metrics["successful"] = count
            elif status == DeliveryStatus.FAILED_ATTEMPT.value:
                metrics["failed"] = count
            elif status == DeliveryStatus.PENDING.value:
                metrics["pending"] = count
            elif status == DeliveryStatus.FINAL_FAILURE.value:
                metrics["final_failure"] = count
        
        # Get additional metrics
        avg_attempts_query = text("""
            SELECT 
                AVG(attempt_number) as avg_attempts
            FROM 
                delivery_logs
            WHERE 
                created_at >= :since
        """)
        
        avg_result = await self.session.execute(avg_attempts_query, {"since": since})
        avg_row = avg_result.fetchone()
        if avg_row and avg_row._mapping["avg_attempts"]:
            metrics["avg_attempts"] = float(avg_row._mapping["avg_attempts"])
        else:
            metrics["avg_attempts"] = 0.0
        
        return metrics