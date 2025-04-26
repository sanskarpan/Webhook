"""
Service for subscription-related business logic.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_cache import RedisCache
from app.db.repositories.subscription_repository import SubscriptionRepository
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate


class SubscriptionService:
    """Service layer for subscription-related operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.repository = SubscriptionRepository(session)
    
    async def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            subscription_data: Subscription data
            
        Returns:
            Created subscription
        """
        subscription = await self.repository.create(subscription_data)
        
        # Cache the subscription data
        self._cache_subscription(subscription)
        
        return subscription
    
    async def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """
        Get a subscription by ID, with caching.
        
        Args:
            subscription_id: Subscription UUID
            
        Returns:
            Subscription if found, None otherwise
        """
        # Try to get from cache first
        cached_subscription = self._get_cached_subscription(subscription_id)
        if cached_subscription:
            return cached_subscription
        
        # If not in cache, get from database
        subscription = await self.repository.get_by_id(subscription_id)
        
        # Cache the result if found
        if subscription:
            self._cache_subscription(subscription)
        
        return subscription
    
    async def list_subscriptions(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Subscription], int]:
        """
        List subscriptions with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of subscriptions, total count)
        """
        subscriptions = await self.repository.list(skip=skip, limit=limit)
        total = await self.repository.count()
        return subscriptions, total
    
    async def update_subscription(
        self, subscription_id: UUID, subscription_data: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """
        Update a subscription.
        
        Args:
            subscription_id: Subscription UUID
            subscription_data: Updated subscription data
            
        Returns:
            Updated subscription if found, None otherwise
        """
        subscription = await self.repository.update(subscription_id, subscription_data)
        
        # Update cache if the update was successful
        if subscription:
            self._cache_subscription(subscription)
            
        return subscription
    
    async def delete_subscription(self, subscription_id: UUID) -> bool:
        """
        Delete a subscription.
        
        Args:
            subscription_id: Subscription UUID
            
        Returns:
            True if deleted, False if not found
        """
        # Delete from cache
        self._delete_cached_subscription(subscription_id)
        
        # Delete from database
        return await self.repository.delete(subscription_id)
    
    async def check_event_type_allowed(
        self, subscription_id: UUID, event_type: str
    ) -> bool:
        """
        Check if an event type is allowed for a subscription.
        
        Args:
            subscription_id: Subscription UUID
            event_type: Event type to check
            
        Returns:
            True if allowed, False otherwise
        """
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return False
        
        # If no event types specified, all are allowed
        if not subscription.event_types:
            return True
        
        return event_type in subscription.event_types
    
    def _cache_subscription(self, subscription: Subscription) -> None:
        """
        Cache a subscription in Redis.
        
        Args:
            subscription: Subscription to cache
        """
        RedisCache.set(
            key=str(subscription.id),
            value={
                "id": str(subscription.id),
                "target_url": subscription.target_url,
                "secret_key": subscription.secret_key,
                "event_types": subscription.event_types,
                "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
                "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None
            },
            prefix="subscription"
        )
    
    def _get_cached_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """
        Get a subscription from Redis cache.
        
        Args:
            subscription_id: Subscription UUID
            
        Returns:
            Subscription if in cache, None otherwise
        """
        cached_data = RedisCache.get_json(str(subscription_id), prefix="subscription")
        if not cached_data:
            return None
        
        # Convert the cached JSON back to a Subscription object
        from datetime import datetime
        
        created_at = None
        if cached_data.get("created_at"):
            created_at = datetime.fromisoformat(cached_data["created_at"])
        
        updated_at = None
        if cached_data.get("updated_at"):
            updated_at = datetime.fromisoformat(cached_data["updated_at"])
            
        return Subscription(
            id=UUID(cached_data["id"]),
            target_url=cached_data["target_url"],
            secret_key=cached_data["secret_key"],
            event_types=cached_data["event_types"],
            created_at=created_at,
            updated_at=updated_at
        )
    
    def _delete_cached_subscription(self, subscription_id: UUID) -> None:
        """
        Delete a subscription from Redis cache.
        
        Args:
            subscription_id: Subscription UUID
        """
        RedisCache.delete(str(subscription_id), prefix="subscription")