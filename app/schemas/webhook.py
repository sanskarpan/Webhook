"""
Pydantic schemas for webhook-related requests and responses.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, RootModel


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
    
    class Config:
        json_schema_extra = {
            "example": {
                "webhook_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "subscription_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
                "event_type": "order.created",
                "message": "Webhook accepted for delivery"
            }
        }


class OrderItem(BaseModel):
    """Item in an order."""
    product_id: str = Field(description="Product identifier")
    quantity: int = Field(description="Number of items")
    price: Optional[float] = Field(default=None, description="Price per item")


class OrderCreatedPayload(BaseModel):
    """Example schema for an order created event."""
    order_id: str = Field(description="Order identifier")
    customer_id: str = Field(description="Customer identifier")
    items: List[OrderItem] = Field(description="List of items in the order")
    total: float = Field(description="Total order amount")
    status: str = Field(description="Order status")
    created_at: str = Field(description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD-12345",
                "customer_id": "CUST-6789",
                "items": [
                    {"product_id": "PROD-101", "quantity": 2, "price": 29.99},
                    {"product_id": "PROD-205", "quantity": 1, "price": 49.99}
                ],
                "total": 109.97,
                "status": "confirmed",
                "created_at": "2023-04-25T10:15:30Z"
            }
        }


class UserRegisteredPayload(BaseModel):
    """Example schema for a user registered event."""
    user_id: str = Field(description="User identifier")
    email: str = Field(description="User's email address")
    name: str = Field(description="User's full name")
    created_at: str = Field(description="Registration timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR-7890",
                "email": "user@example.com",
                "name": "John Doe",
                "created_at": "2023-04-25T10:15:30Z"
            }
        }


# We'll keep this for backward compatibility, but it won't be used in the API directly
class WebhookPayload(RootModel[Dict[str, Any]]):
    """
    Generic representation of a webhook payload.
    
    Since we accept arbitrary JSON, we use a Dict[str, Any] type.
    """
    model_config = {
        "json_schema_extra": {
            "description": "The JSON payload for the webhook",
            "example": {
                "order_id": "ORD-12345",
                "customer_id": "CUST-6789",
                "items": [
                    {"product_id": "PROD-101", "quantity": 2, "price": 29.99},
                    {"product_id": "PROD-205", "quantity": 1, "price": 49.99}
                ],
                "total": 109.97,
                "status": "confirmed",
                "created_at": "2023-04-25T10:15:30Z"
            }
        }
    }


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
    
    class Config:
        json_schema_extra = {
            "example": {
                "payload": {
                    "order_id": "ORD-12345",
                    "status": "confirmed",
                    "total": 109.97,
                    "items": [
                        {"product_id": "PROD-101", "quantity": 2},
                        {"product_id": "PROD-205", "quantity": 1}
                    ]
                },
                "event_type": "order.created"
            }
        }


class WebhookIngestionFailure(BaseModel):
    """Response model for webhook ingestion failures."""
    error: str = Field(description="Error message")
    detail: str | Dict[str, Any] = Field(description="Detailed error information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid signature",
                "detail": {
                    "error": "Invalid signature",
                    "detail": "The provided signature does not match the expected signature",
                    "debug_info": {
                        "received": "sha256=1234567890abcdef",
                        "note": "Signatures are calculated using canonical JSON representation with sorted keys"
                    }
                }
            }
        }