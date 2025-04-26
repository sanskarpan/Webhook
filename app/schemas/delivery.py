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
    status: str = Field(description="Status of this delivery attempt")
    http_status: Optional[int] = Field(
        default=None,
        description="HTTP status code received from the target URL"
    )
    error_details: Optional[str] = Field(
        default=None,
        description="Error details if attempt failed"
    )
    timestamp: datetime = Field(description="When this attempt was made")
    
    class Config:
        json_schema_extra = {
            "example": {
                "attempt_number": 1,
                "status": "SUCCESS",
                "http_status": 200,
                "error_details": None,
                "timestamp": "2023-04-25T10:20:30Z"
            }
        }


class DeliveryAttemptResponse(DeliveryAttemptBase):
    """Response model for a single delivery attempt."""
    id: UUID = Field(description="Unique identifier for this delivery attempt")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "attempt_number": 2,
                "status": "FAILED_ATTEMPT",
                "http_status": 500,
                "error_details": "Internal Server Error at target endpoint",
                "timestamp": "2023-04-25T10:20:45Z"
            }
        }


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
    status: str = Field(description="Current delivery status")
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
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "webhook_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
                "subscription_id": "5fa85f64-5717-4562-b3fc-2c963f66afa8",
                "target_url": "https://example.com/webhook-receiver",
                "event_type": "order.created",
                "created_at": "2023-04-25T10:15:30Z",
                "status": "SUCCESS",
                "next_retry_at": None,
                "attempts": [
                    {
                        "attempt_number": 1,
                        "status": "SUCCESS",
                        "http_status": 200,
                        "error_details": None,
                        "timestamp": "2023-04-25T10:15:35Z"
                    }
                ]
            }
        }


class DeliveryAttemptList(BaseModel):
    """Response model for a list of delivery attempts."""
    items: List[DeliveryAttemptResponse]
    total: int
    subscription_id: UUID
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "attempt_number": 1,
                        "status": "SUCCESS",
                        "http_status": 200,
                        "error_details": None,
                        "timestamp": "2023-04-25T10:15:35Z"
                    },
                    {
                        "id": "6fa85f64-5717-4562-b3fc-2c963f66afa9",
                        "attempt_number": 1,
                        "status": "FAILED_ATTEMPT",
                        "http_status": 503,
                        "error_details": "Service Unavailable",
                        "timestamp": "2023-04-25T11:20:30Z"
                    }
                ],
                "total": 2,
                "subscription_id": "5fa85f64-5717-4562-b3fc-2c963f66afa8"
            }
        }


class DeliveryStatusSummary(BaseModel):
    """Summary of delivery status for a webhook or subscription."""
    total_attempts: int = Field(description="Total number of delivery attempts")
    successful: int = Field(description="Number of successful deliveries")
    failed: int = Field(description="Number of failed delivery attempts")
    pending: int = Field(description="Number of pending delivery attempts")
    final_failure: int = Field(description="Number of webhooks that failed all retries")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_attempts": 150,
                "successful": 120,
                "failed": 25,
                "pending": 5,
                "final_failure": 10
            }
        }


class WebhookDetailsResponse(BaseModel):
    """Response model with complete webhook delivery information."""
    webhook_id: UUID = Field(description="Unique identifier for this webhook")
    subscription_id: UUID = Field(description="ID of the subscription this webhook belongs to")
    event_type: Optional[str] = Field(
        default=None, 
        description="Type of event (e.g., 'order.created', 'user.registered')"
    )
    payload: Dict[str, Any] = Field(description="The JSON payload data of the webhook")
    status: str = Field(description="Current delivery status (success, failed_attempt, final_failure, pending)")
    attempts: List[DeliveryAttemptBase] = Field(
        description="List of all delivery attempts made for this webhook"
    )
    created_at: datetime = Field(description="When this webhook was initially received")
    updated_at: datetime = Field(description="When this webhook record was last updated")
    next_retry_at: Optional[datetime] = Field(
        default=None, 
        description="When the next delivery attempt is scheduled (if applicable)"
    )
    target_url: str = Field(description="The URL where this webhook is being delivered to")
    last_attempt_at: Optional[datetime] = Field(
        default=None,
        description="When the most recent delivery attempt was made"
    )
    statistics: Optional[Dict[str, int]] = Field(
        default=None,
        description="Summary statistics about delivery attempts (counts by status)"
    )

    class Config:
        """Pydantic config."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "webhook_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "subscription_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
                "event_type": "order.created",
                "payload": {
                    "order_id": "ORD-12345",
                    "status": "confirmed",
                    "total": 99.99
                },
                "status": "PROCESSING",
                "attempts": [
                    {
                        "attempt_number": 1,
                        "status": "FAILED_ATTEMPT",
                        "http_status": 500,
                        "error_details": "Internal Server Error",
                        "timestamp": "2023-04-25T10:20:30Z"
                    }
                ],
                "created_at": "2023-04-25T10:20:00Z",
                "updated_at": "2023-04-25T10:20:30Z",
                "next_retry_at": "2023-04-25T10:22:30Z",
                "target_url": "https://example.com/webhook",
                "last_attempt_at": "2023-04-25T10:20:30Z",
                "statistics": {
                    "total_attempts": 1,
                    "successful": 0,
                    "failed": 1,
                    "pending": 0,
                    "final_failure": 0
                }
            }
        }