"""
Pydantic schemas for subscription-related requests and responses.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl, BaseModel, Field, validator


class SubscriptionBase(BaseModel):
    """Base shared subscription properties."""
    target_url: AnyUrl = Field(
        description="The URL where webhook payloads will be delivered via POST"
    )
    secret_key: Optional[str] = Field(
        default=None,
        description="Optional secret key used for HMAC-SHA256 signature verification"
    )
    event_types: Optional[List[str]] = Field(
        default=None,
        description="List of event types this subscription is interested in. If None, all events are allowed."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_url": "https://example.com/webhook-receiver",
                "secret_key": "your-secret-key-for-signing",
                "event_types": ["order.created", "order.updated", "user.registered"]
            }
        }


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription."""
    pass


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription."""
    target_url: Optional[AnyUrl] = Field(
        default=None,
        description="The URL where webhook payloads will be delivered via POST"
    )
    secret_key: Optional[str] = Field(
        default=None,
        description="Optional secret key used for HMAC-SHA256 signature verification"
    )
    event_types: Optional[List[str]] = Field(
        default=None,
        description="List of event types this subscription is interested in. If None, all events are allowed."
    )

    @validator('event_types')
    def validate_event_types(cls, v):
        """Validate that event_types list is properly formatted."""
        if v is not None:
            # Ensure all event types follow the expected format
            for event_type in v:
                if not event_type or not isinstance(event_type, str):
                    raise ValueError("Event types must be non-empty strings")
                
                # Optional: enforce naming convention like "resource.action"
                if '.' not in event_type:
                    raise ValueError(
                        f"Event type '{event_type}' does not follow the 'resource.action' format"
                    )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_url": "https://example.com/new-webhook-endpoint",
                "secret_key": "updated-secret-key",
                "event_types": ["order.created", "order.canceled"]
            }
        }


class SubscriptionInDB(SubscriptionBase):
    """Schema for subscription stored in database."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "target_url": "https://example.com/webhook-receiver",
                "secret_key": "your-secret-key-for-signing",
                "event_types": ["order.created", "order.updated"],
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z"
            }
        }


class SubscriptionResponse(SubscriptionInDB):
    """Schema for subscription responses."""
    pass


class SubscriptionList(BaseModel):
    """Schema for a list of subscriptions."""
    items: List[SubscriptionResponse]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "target_url": "https://example.com/webhook-receiver",
                        "secret_key": "secret-key-1",
                        "event_types": ["order.created", "order.updated"],
                        "created_at": "2023-01-01T12:00:00Z",
                        "updated_at": "2023-01-01T12:00:00Z"
                    },
                    {
                        "id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
                        "target_url": "https://another-example.com/webhooks",
                        "secret_key": "secret-key-2",
                        "event_types": ["user.created", "user.updated"],
                        "created_at": "2023-01-02T12:00:00Z",
                        "updated_at": "2023-01-02T12:00:00Z"
                    }
                ],
                "total": 2
            }
        }


class SubscriptionStatus(BaseModel):
    """Schema for subscription status check."""
    id: UUID
    active: bool
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    pending_deliveries: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "active": True,
                "total_deliveries": 125,
                "successful_deliveries": 110,
                "failed_deliveries": 10,
                "pending_deliveries": 5
            }
        }