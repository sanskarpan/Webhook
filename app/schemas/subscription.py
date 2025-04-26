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


class SubscriptionInDB(SubscriptionBase):
    """Schema for subscription stored in database."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


class SubscriptionResponse(SubscriptionInDB):
    """Schema for subscription responses."""
    pass


class SubscriptionList(BaseModel):
    """Schema for a list of subscriptions."""
    items: List[SubscriptionResponse]
    total: int


class SubscriptionStatus(BaseModel):
    """Schema for subscription status check."""
    id: UUID
    active: bool
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    pending_deliveries: int