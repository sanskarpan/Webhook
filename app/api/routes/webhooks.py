"""
API routes for webhook ingestion.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import (APIRouter, Body, Depends, Header, HTTPException, Path, Query, status)

from app.api.deps import get_webhook_service
from app.schemas.webhook import WebhookIngestionResponse
from app.services.webhook_service import WebhookService
from app.utils.signature import parse_signature_header

router = APIRouter(prefix="/ingest", tags=["webhooks"])


@router.post(
    "/{subscription_id}",
    response_model=WebhookIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a webhook for delivery"
)
async def ingest_webhook(
    payload: Dict[str, Any] = Body(..., description="Webhook payload (JSON)"),
    subscription_id: UUID = Path(..., description="The ID of the subscription to deliver to"),
    event_type: Optional[str] = Query(
        None, 
        description="The type of event (e.g., 'order.created')"
    ),
    x_hub_signature_256: Optional[str] = Header(
        None,
        description="HMAC-SHA256 signature for payload verification",
        alias="X-Hub-Signature-256"
    ),
    service: WebhookService = Depends(get_webhook_service)
):
    """
    Ingest a webhook for asynchronous delivery.
    
    The webhook payload will be:
    1. Verified against the signature if provided
    2. Checked against allowed event types for the subscription
    3. Queued for asynchronous delivery
    4. Delivery attempts will be made with configurable retries on failures
    
    Returns a webhook ID that can be used to check delivery status.
    """
    signature = parse_signature_header(x_hub_signature_256)
    
    webhook_id, accepted = await service.process_webhook(
        subscription_id=subscription_id,
        payload=payload,
        event_type=event_type,
        signature=signature
    )
    
    return {
        "webhook_id": webhook_id,
        "subscription_id": subscription_id,
        "event_type": event_type,
        "message": "Webhook accepted for delivery"
    }