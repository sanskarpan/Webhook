"""
API routes for subscription management.
"""
import logging
from typing import List, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.deps import get_delivery_service, get_subscription_service
from app.schemas.delivery import DeliveryAttemptList, DeliveryLogResponse, DeliveryAttemptResponse
from app.schemas.subscription import (SubscriptionCreate, SubscriptionList, SubscriptionResponse, SubscriptionUpdate)
from app.services.delivery_service import DeliveryService
from app.services.subscription_service import SubscriptionService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new webhook subscription",
    description=(
        "Create a new webhook subscription for receiving webhook deliveries.\n\n"
        "**Required fields:**\n"
        "* **target_url**: The URL where webhook payloads will be delivered via POST\n\n"
        "**Optional fields:**\n"
        "* **secret_key**: Secret key for HMAC-SHA256 signature verification\n"
        "* **event_types**: List of event types this subscription should receive (if omitted, receives all events)"
    )
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
    try:
        logger.info(f"Creating new subscription with target URL: {subscription.target_url}")
        created = await service.create_subscription(subscription)
        logger.info(f"Subscription created successfully with ID: {created.id}")
        return created
    except ConnectionError as e:
        logger.error(f"Database connection error during subscription creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating subscription: {str(e)}"
        )


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get a specific subscription",
    description="Retrieve the details of a specific webhook subscription by its unique identifier."
)
async def get_subscription(
    subscription_id: UUID = Path(..., description="The ID of the subscription"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get a specific webhook subscription by ID.
    """
    try:
        logger.info(f"Getting subscription with ID: {subscription_id}")
        subscription = await service.get_subscription(subscription_id)
        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        return subscription
    except HTTPException:
        raise
    except ConnectionError as e:
        logger.error(f"Database connection error while retrieving subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Error retrieving subscription {subscription_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving subscription: {str(e)}"
        )


@router.get(
    "",
    response_model=SubscriptionList,
    summary="List all subscriptions",
    description=(
        "List all webhook subscriptions with pagination support.\n\n"
        "Results can be paginated using the skip and limit parameters. "
        "The response includes the total count of subscriptions and the requested page of items."
    )
)
async def list_subscriptions(
    skip: int = Query(0, ge=0, description="Number of subscriptions to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of subscriptions to return"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    List all webhook subscriptions with pagination.
    """
    try:
        logger.info(f"Listing subscriptions with skip={skip}, limit={limit}")
        subscriptions, total = await service.list_subscriptions(skip=skip, limit=limit)
        return {
            "items": subscriptions,
            "total": total
        }
    except ConnectionError as e:
        logger.error(f"Database connection error while listing subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Error listing subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing subscriptions: {str(e)}"
        )


@router.put(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update a subscription",
    description=(
        "Update an existing webhook subscription.\n\n"
        "**Fields that can be updated:**\n"
        "* **target_url**: The URL where webhook payloads will be delivered\n"
        "* **secret_key**: Secret key for HMAC-SHA256 signature verification\n"
        "* **event_types**: List of event types this subscription is interested in\n\n"
        "Only include the fields you want to change. Omitted fields will remain unchanged."
    )
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
    try:
        logger.info(f"Updating subscription with ID: {subscription_id}")
        updated = await service.update_subscription(subscription_id, subscription_data)
        if not updated:
            logger.warning(f"Subscription not found for update: {subscription_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        logger.info(f"Subscription {subscription_id} updated successfully")
        return updated
    except HTTPException:
        raise
    except ConnectionError as e:
        logger.error(f"Database connection error while updating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Error updating subscription {subscription_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating subscription: {str(e)}"
        )


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a subscription",
    response_model=Dict[str, str],
    description=(
        "Permanently delete a webhook subscription and stop receiving webhooks.\n\n"
        "**Important notes:**\n"
        "* This action cannot be undone\n"
        "* All webhook delivery history for this subscription will be preserved\n"
        "* Webhook deliveries currently in progress will complete\n"
        "* Any pending webhooks in the queue will be canceled\n\n"
        "Returns a success message with the deleted subscription ID."
    ),
    responses={
        200: {
            "description": "Subscription successfully deleted",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Subscription 3fa85f64-5717-4562-b3fc-2c963f66afa6 has been successfully deleted"
                    }
                }
            }
        },
        404: {
            "description": "Subscription not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Subscription not found"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error deleting subscription: database error"
                    }
                }
            }
        }
    }
)
async def delete_subscription(
    subscription_id: UUID = Path(..., description="The ID of the subscription to delete"),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Delete a webhook subscription.
    """
    try:
        logger.info(f"Deleting subscription with ID: {subscription_id}")
        deleted = await service.delete_subscription(subscription_id)
        if not deleted:
            logger.warning(f"Subscription not found for deletion: {subscription_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        logger.info(f"Subscription {subscription_id} deleted successfully")
        return {"message": f"Subscription {subscription_id} has been successfully deleted"}
    except HTTPException:
        raise
    except ConnectionError as e:
        logger.error(f"Database connection error while deleting subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Error deleting subscription {subscription_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting subscription: {str(e)}"
        )


@router.get(
    "/{subscription_id}/attempts",
    response_model=DeliveryAttemptList,
    summary="List recent delivery attempts for a subscription",
    description=(
        "Get recent webhook delivery attempts for a specific subscription.\n\n"
        "This endpoint returns a list of delivery attempts sorted by time, including:\n"
        "* Attempt number\n"
        "* Status (success, failed, pending)\n"
        "* HTTP status code\n"
        "* Error details (if any)\n"
        "* Timestamp\n\n"
        "Use this endpoint to troubleshoot delivery issues for a specific subscription."
    )
)
async def get_subscription_attempts(
    subscription_id: UUID = Path(..., description="The ID of the subscription"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of delivery attempts to return"),
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """
    Get recent webhook delivery attempts for a specific subscription.
    """
    try:
        logger.info(f"Getting delivery attempts for subscription ID: {subscription_id}")
        delivery_logs = await delivery_service.get_delivery_attempts(
            subscription_id=subscription_id,
            limit=limit
        )
        
        # Manually convert DeliveryLog objects to DeliveryAttemptResponse objects
        attempts = []
        for log in delivery_logs:
            attempt = DeliveryAttemptResponse(
                id=log.id,
                attempt_number=log.attempt_number,
                status=log.status.value if log.status else "pending",  # Convert enum to string
                http_status=log.http_status,
                error_details=log.error_details,
                timestamp=log.updated_at or log.created_at
            )
            attempts.append(attempt)
        
        return {
            "items": attempts,
            "total": len(attempts),
            "subscription_id": subscription_id
        }
    except ConnectionError as e:
        logger.error(f"Database connection error while retrieving delivery attempts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    except Exception as e:
        logger.exception(f"Error retrieving delivery attempts for subscription {subscription_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving delivery attempts: {str(e)}"
        )