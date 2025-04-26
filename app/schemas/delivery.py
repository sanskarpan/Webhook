"""
Pydantic schemas for delivery log and status-related requests and responses.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.delivery_log import DeliveryStatus


class DeliveryAttemptBase(BaseModel):
    """Base model for delivery attempt information."""
    attempt_number: int = Field(description="Delivery attempt number (1-based)")
    status: DeliveryStatus = Field(description="Status of this delivery attempt")
    http_status: Optional[int] = Field(
        default=None,
        description="HTTP status code received from the target URL"
    )
    error_details: Optional[str] = Field(
        default=None,
        description="Error details if attempt failed"
    )
    timestamp: datetime = Field(description="When this attempt was made")


class DeliveryAttemptResponse(DeliveryAttemptBase):
    """Response model for a single delivery attempt."""
    id: UUID = Field(description="Unique identifier for this delivery attempt")


class DeliveryLogResponse(BaseModel):
    """Response model for delivery log information."""
    id: UUID = Field(description="Unique identifier for this delivery log")
    webhook_id: UUID = Field(description="ID of the webhook being delivered")
    subscription_id: UUID = Field(description="ID of the subscription this webhook is for")
    target_url: str = Field(description="Target URL for delivery")
    event_type: Optional[str] = Field(
        default=None,
        description="Event type for this webhook"
    )
    created_at: datetime = Field(description="When this webhook was received")
    status: DeliveryStatus = Field(description="Current delivery status")
    next_retry_at: Optional[datetime] = Field(
        default=None,
        description="When next retry is scheduled (if any)"
    )
    attempts: List[DeliveryAttemptBase] = Field(
        default_factory=list,
        description="List of delivery attempts"
    )
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class DeliveryAttemptList(BaseModel):
    """Response model for a list of delivery attempts."""
    items: List[DeliveryAttemptResponse]
    total: int
    subscription_id: UUID


class DeliveryStatusSummary(BaseModel):
    """Summary of delivery status for a webhook or subscription."""
    total_attempts: int = Field(description="Total number of delivery attempts")
    successful: int = Field(description="Number of successful deliveries")
    failed: int = Field(description="Number of failed delivery attempts")
    pending: int = Field(description="Number of pending delivery attempts")
    final_failure: int = Field(description="Number of webhooks that failed all retries")


class WebhookDetailsResponse(BaseModel):
    """Response model with complete webhook delivery information."""
    webhook_id: UUID
    subscription_id: UUID
    event_type: Optional[str] = None
    payload: Dict[str, Any]
    status: DeliveryStatus
    attempts: List[DeliveryAttemptBase]
    created_at: datetime
    updated_at: datetime
    next_retry_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""
        from_attributes = True