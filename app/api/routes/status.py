"""
API routes for webhook delivery status.
"""
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status, Query

from app.api.deps import get_delivery_service, get_webhook_service
from app.schemas.delivery import DeliveryStatusSummary, WebhookDetailsResponse
from app.services.delivery_service import DeliveryService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/status", tags=["status"])


@router.get(
    "/{webhook_id}",
    response_model=WebhookDetailsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get webhook delivery status",
    description=(
        "Get detailed status information about a webhook delivery.\n\n"
        "This endpoint provides comprehensive information about a specific webhook delivery, "
        "including all delivery attempts, current status, and scheduling information.\n\n"
        "**Use this endpoint to:**\n"
        "* Check if a webhook was delivered successfully\n"
        "* View detailed delivery history for troubleshooting\n"
        "* Monitor pending retries and their scheduled times\n"
        "* Access the full webhook payload\n\n"
        "**Response includes:**\n"
        "* Webhook metadata (ID, subscription, event type)\n"
        "* Current delivery status\n"
        "* Complete delivery attempt history with HTTP status codes\n"
        "* Timestamps for creation, updates, and next retry (if applicable)\n"
        "* Target URL where webhook is being delivered\n"
        "* Original payload content\n"
        "* Delivery statistics"
    )
)
async def get_webhook_status(
    webhook_id: UUID = Path(
        ..., 
        description="The ID of the webhook to check"
    ),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Get detailed status information about a webhook delivery.
    
    Returns:
    - Current delivery status
    - Complete delivery attempt history
    - Timestamps for creation, last attempt, and next retry (if applicable)
    - Target URL and payload details
    - Statistics about delivery attempts
    """
    try:
        webhook_details = await service.get_webhook_status(webhook_id=webhook_id)
        if not webhook_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook with ID {webhook_id} not found"
            )
        return webhook_details
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving webhook status: {str(e)}"
        )


@router.get(
    "/metrics/summary",
    response_model=DeliveryStatusSummary,
    status_code=status.HTTP_200_OK,
    summary="Get webhook delivery metrics",
    description=(
        "Get detailed delivery performance metrics for a specified time window.\n\n"
        "**This endpoint provides:**\n"
        "* Total number of webhooks processed\n"
        "* Success rate statistics\n"
        "* Failure statistics and reasons\n"
        "* Pending delivery counts\n"
        "* Final failure counts (webhooks that exhausted all retry attempts)\n\n"
        "**Use cases:**\n"
        "* Monitoring overall system health\n"
        "* Tracking delivery performance over time\n"
        "* Setting up alerts for high error rates\n"
        "* Identifying patterns in webhook delivery issues\n\n"
        "The time window can be adjusted using the hours query parameter (1-72 hours)."
    ),
    responses={
        200: {
            "description": "Successful retrieval of delivery metrics",
            "content": {
                "application/json": {
                    "example": {
                        "total_attempts": 150,
                        "successful": 120,
                        "failed": 25,
                        "pending": 5,
                        "final_failure": 10
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error retrieving delivery metrics: database connection error"
                    }
                }
            }
        }
    }
)
async def get_delivery_metrics(
    hours: int = Query(
        24, 
        description="Time window in hours (default: last 24 hours)",
        ge=1,
        le=72
    ),
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """
    Get delivery metrics for the specified time period.
    
    Returns a summary of webhook delivery statistics over the specified time window.
    """
    try:
        metrics = await delivery_service.get_delivery_metrics(hours=hours)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving delivery metrics: {str(e)}"
        )