"""
Pydantic schemas for webhook-related requests and responses.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookIngestionResponse(BaseModel):
    """Response model for webhook ingestion requests."""
    webhook_id: UUID = Field(description="The unique identifier for this webhook delivery")
    subscription_id: UUID = Field(description="The subscription this webhook will be delivered to")
    event_type: Optional[str] = Field(
        default=None,
        description="The event type associated with this webhook"
    )
    message: str = Field(
        default="Webhook accepted for delivery",
        description="Status message"
    )


class WebhookPayload(BaseModel):
    """
    Generic representation of a webhook payload.
    
    Since we accept arbitrary JSON, we use a Dict[str, Any] type.
    """
    __root__: Dict[str, Any] = Field(
        description="The JSON payload for the webhook"
    )


class WebhookRequest(BaseModel):
    """
    Request model for webhook ingestion.
    
    Note: This isn't directly used by the API since we accept raw JSON,
    but it's helpful for documentation purposes.
    """
    payload: Dict[str, Any] = Field(
        description="The JSON payload to be sent to the target URL"
    )
    event_type: Optional[str] = Field(
        default=None,
        description="The type of event (e.g., 'order.created')"
    )


class WebhookIngestionFailure(BaseModel):
    """Response model for webhook ingestion failures."""
    error: str = Field(description="Error message")
    detail: str = Field(description="Detailed error information")