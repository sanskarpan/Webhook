"""
Repository for subscription-related database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate


class SubscriptionRepository:
    """Repository for subscription-related database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(self, subscription_data: SubscriptionCreate) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            subscription_data: Subscription data
            
        Returns:
            Created subscription instance
        """
        subscription = Subscription(
            target_url=str(subscription_data.target_url),
            secret_key=subscription_data.secret_key,
            event_types=subscription_data.event_types
        )
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription
    
    async def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        """
        Get a subscription by ID.
        
        Args:
            subscription_id: Subscription UUID
            
        Returns:
            Subscription if found, None otherwise
        """
        query = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def list(self, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """
        List subscriptions with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of subscriptions
        """
        query = select(Subscription).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        subscription_id: UUID,
        subscription_data: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """
        Update a subscription.
        
        Args:
            subscription_id: Subscription UUID
            subscription_data: Updated subscription data
            
        Returns:
            Updated subscription if found, None otherwise
        """
        subscription = await self.get_by_id(subscription_id)
        if not subscription:
            return None
        
        # Update only provided fields
        update_data = subscription_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Handle AnyUrl conversion to string for target_url
            if field == "target_url" and value is not None:
                value = str(value)
            setattr(subscription, field, value)
        
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription
    
    async def delete(self, subscription_id: UUID) -> bool:
        """
        Delete a subscription.
        
        Args:
            subscription_id: Subscription UUID
            
        Returns:
            True if deleted, False if not found
        """
        query = delete(Subscription).where(Subscription.id == subscription_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def count(self) -> int:
        """
        Count total subscriptions.
        
        Returns:
            Total number of subscriptions
        """
        query = select(func.count()).select_from(Subscription)
        result = await self.session.execute(query)
        return result.scalar_one()