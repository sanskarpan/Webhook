"""
DeliveryLog model definition.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class DeliveryStatus(str, enum.Enum):
    """Enum for webhook delivery status."""
    SUCCESS = "success"
    FAILED_ATTEMPT = "failed_attempt"  # Temporary failure, will retry
    FINAL_FAILURE = "final_failure"    # All retries exhausted
    PENDING = "pending"                # Not yet attempted


class DeliveryLog(Base):
    """
    Model for tracking webhook delivery attempts.
    
    Logs each delivery attempt including status, HTTP code, and error details.
    Used for both tracking current status and for analytics/debugging.
    """
    __tablename__ = "delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Webhook metadata
    webhook_id = Column(
        UUID(as_uuid=True), 
        nullable=False, 
        index=True
    )
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_url = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    event_type = Column(String(100), nullable=True, index=True)
    
    # Delivery attempt details
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(
        Enum(DeliveryStatus, name='deliverystatus', create_constraint=True, native_enum=True),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True
    )
    http_status = Column(Integer, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Timing info
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    subscription = relationship("Subscription", backref="delivery_logs")
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DeliveryLog(id={self.id}, "
            f"webhook_id={self.webhook_id}, "
            f"attempt={self.attempt_number}, "
            f"status={self.status})>"
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the delivery log to a dictionary."""
        return {
            "id": str(self.id),
            "webhook_id": str(self.webhook_id),
            "subscription_id": str(self.subscription_id),
            "target_url": self.target_url,
            "payload": self.payload,
            "event_type": self.event_type,
            "attempt_number": self.attempt_number,
            "status": self.status.value if self.status else None,
            "http_status": self.http_status,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None
        }