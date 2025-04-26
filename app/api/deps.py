"""
Dependencies for API routes.
"""
from typing import AsyncGenerator, Generator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.delivery_service import DeliveryService
from app.services.subscription_service import SubscriptionService
from app.services.webhook_service import WebhookService


async def get_subscription_service(
    db: AsyncSession = Depends(get_async_db)
) -> SubscriptionService:
    """
    Dependency for getting a SubscriptionService instance.
    
    Args:
        db: Async database session
        
    Returns:
        SubscriptionService instance
    """
    return SubscriptionService(db)


async def get_webhook_service(
    db: AsyncSession = Depends(get_async_db)
) -> WebhookService:
    """
    Dependency for getting a WebhookService instance.
    
    Args:
        db: Async database session
        
    Returns:
        WebhookService instance
    """
    return WebhookService(db)


async def get_delivery_service(
    db: AsyncSession = Depends(get_async_db)
) -> DeliveryService:
    """
    Dependency for getting a DeliveryService instance.
    
    Args:
        db: Async database session
        
    Returns:
        DeliveryService instance
    """
    return DeliveryService(db)