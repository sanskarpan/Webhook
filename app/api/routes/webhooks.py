"""
API routes for webhook ingestion.
"""
from typing import Any, Dict, Optional, Union, Annotated
from uuid import UUID

from fastapi import (APIRouter, Body, Depends, Header, HTTPException, Path, Query, status)

from app.api.deps import get_webhook_service
from app.schemas.webhook import (WebhookIngestionFailure, WebhookIngestionResponse, 
                               OrderCreatedPayload, UserRegisteredPayload)
from app.services.webhook_service import WebhookService
from app.utils.signature import parse_signature_header

router = APIRouter(prefix="/ingest", tags=["webhooks"])


@router.post(
    "/{subscription_id}",
    response_model=WebhookIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a webhook for delivery",
    description=(
        "Ingest a webhook payload for asynchronous delivery to a subscription endpoint.\n\n"
        "**This endpoint:**\n"
        "* Validates the payload against the subscription\n"
        "* Verifies the signature if provided\n"
        "* Filters based on event type if specified\n"
        "* Queues the webhook for asynchronous delivery\n\n"
        "**The system will automatically:**\n"
        "* Deliver the webhook to the target URL\n"
        "* Retry failed deliveries with exponential backoff\n"
        "* Track all delivery attempts\n"
        "* Update delivery status\n\n"
        "Returns a webhook ID that can be used to track delivery status."
    ),
    responses={
        202: {
            "description": "Webhook accepted for delivery",
            "model": WebhookIngestionResponse
        },
        400: {
            "description": "Invalid request or signature",
            "model": WebhookIngestionFailure
        },
        404: {
            "description": "Subscription not found",
            "model": WebhookIngestionFailure
        },
        422: {
            "description": "Validation error",
            "model": WebhookIngestionFailure
        },
    },
)

async def ingest_webhook(
    payload: Annotated[
        Union[OrderCreatedPayload, UserRegisteredPayload, Dict[str, Any]],
        Body(
            ...,
            description="Webhook payload to be delivered",
            examples={
                "order_created": {
                    "summary": "Order created event",
                    "value": {
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
                },
                "user_registered": {
                    "summary": "User registration event",
                    "value": {
                        "user_id": "USR-7890",
                        "email": "user@example.com",
                        "name": "John Doe",
                        "created_at": "2023-04-25T10:15:30Z"
                    }
                },
                "custom_payload": {
                    "summary": "Custom event payload",
                    "value": {
                        "event_name": "custom.event",
                        "timestamp": "2023-04-25T10:15:30Z",
                        "data": {
                            "key1": "value1",
                            "key2": "value2"
                        }
                    }
                }
            }
        )
    ],
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
    try:
        signature = parse_signature_header(x_hub_signature_256)
        
        # Convert payload to dict if it's one of our Pydantic models
        # Handle both Pydantic v1 (dict) and v2 (model_dump) methods
        if hasattr(payload, 'model_dump'):
            payload_dict = payload.model_dump()
        elif hasattr(payload, 'dict'):
            payload_dict = payload.dict()
        else:
            payload_dict = payload
        
        webhook_id, accepted = await service.process_webhook(
            subscription_id=subscription_id,
            payload=payload_dict,
            event_type=event_type,
            signature=signature
        )
        
        if not accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Webhook rejected",
                    "detail": "Webhook could not be accepted due to validation or filtering rules"
                }
            )
        
        return {
            "webhook_id": webhook_id,
            "subscription_id": subscription_id,
            "event_type": event_type,
            "message": "Webhook accepted for delivery"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request", "detail": str(e)}
        )