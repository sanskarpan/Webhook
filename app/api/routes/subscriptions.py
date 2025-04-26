"""
API routes for subscription management.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.deps import get_delivery_service, get_subscription_service
from app.schemas.delivery import DeliveryAttemptList, DeliveryLogResponse
from app.schemas.subscription import (SubscriptionCreate, SubscriptionList, SubscriptionResponse, SubscriptionUpdate)
from app.services.delivery_service import DeliveryService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new webhook subscription"
)
async def create_subscription(
    subscription: SubscriptionCreate,
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Create a new webhook subscription.
    
    - **target_url**: The URL where webhook payloads will be delivered via POST
    - **secret_key**: Optional secret key for HMAC-SHA256 signature verification
    - **event_types**: Optional list of event types this subscription is interested in
    """
    created = await service.create_subscription(subscription)
    return created


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get a specific subscription"
)
async def get_subscription(
    subscription_id: UUID = Path(..., description="The ID of the subscription"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get a specific webhook subscription by ID.
    """
    subscription = await service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return subscription


@router.get(
    "",
    response_model=SubscriptionList,
    summary="List all subscriptions"
)
async def list_subscriptions(
    skip: int = Query(0, ge=0, description="Number of subscriptions to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of subscriptions to return"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    List all webhook subscriptions with pagination.
    """
    subscriptions, total = await service.list_subscriptions(skip=skip, limit=limit)
    return {
        "items": subscriptions,
        "total": total
    }


@router.put(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update a subscription"
)
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    subscription_id: UUID = Path(..., description="The ID of the subscription to update"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Update an existing webhook subscription.
    
    Fields that can be updated:
    - **target_url**: The URL where webhook payloads will be delivered
    - **secret_key**: Secret key for HMAC-SHA256 signature verification
    - **event_types**: List of event types this subscription is interested in
    
    Omitted fields will remain unchanged.
    """
    updated = await service.update_subscription(subscription_id, subscription_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return updated


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subscription"
)
async def delete_subscription(
    subscription_id: UUID = Path(..., description="The ID of the subscription to delete"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Delete a webhook subscription.
    """
    deleted = await service.delete_subscription(subscription_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return None


@router.get(
    "/{subscription_id}/attempts",
    response_model=DeliveryAttemptList,
    summary="List recent delivery attempts for a subscription"
)
async def get_subscription_attempts(
    subscription_id: UUID = Path(..., description="The ID of the subscription"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of delivery attempts to return"),
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """
    Get recent webhook delivery attempts for a specific subscription.
    """
    attempts = await delivery_service.get_delivery_attempts(
        subscription_id=subscription_id,
        limit=limit
    )
    
    return {
        "items": attempts,
        "total": len(attempts),
        "subscription_id": subscription_id
    }