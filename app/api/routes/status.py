"""
API routes for webhook delivery status.
"""
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import get_webhook_service
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/status", tags=["status"])


@router.get(
    "/{webhook_id}",
    status_code=status.HTTP_200_OK,
    summary="Get webhook delivery status"
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
    return await service.get_webhook_status(webhook_id=webhook_id)