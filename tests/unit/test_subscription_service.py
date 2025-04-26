"""
Unit tests for the subscription service.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from app.services.subscription_service import SubscriptionService


@pytest.fixture
def mock_session():
    """Create a mock database session for testing."""
    mock = AsyncMock(spec=AsyncSession)
    return mock


@pytest.fixture
def subscription_service(mock_session):
    """Create a subscription service with a mock session."""
    return SubscriptionService(mock_session)


class TestSubscriptionService:
    """Test suite for the subscription service."""
    
    async def test_create_subscription(self, subscription_service, mock_session):
        """Test creating a new subscription."""
        # Mock subscription data
        subscription_data = SubscriptionCreate(
            target_url="https://example.com/webhook",
            secret_key="test-secret",
            event_types=["order.created", "order.updated"]
        )
        
        # Mock subscription model
        mock_subscription = Subscription(
            id=uuid.uuid4(),
            target_url="https://example.com/webhook",
            secret_key="test-secret",
            event_types=["order.created", "order.updated"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Setup mock behavior
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        # Use patch to mock the Subscription creation
        with patch('app.services.subscription_service.Subscription', return_value=mock_subscription):
            result = await subscription_service.create_subscription(subscription_data)
            
            # Check that session methods were called
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once()
            
            # Check the returned subscription
            assert result.id == mock_subscription.id
            assert result.target_url == subscription_data.target_url
            assert result.secret_key == subscription_data.secret_key
            assert result.event_types == subscription_data.event_types
    
    async def test_get_subscription(self, subscription_service, mock_session):
        """Test getting a subscription by ID."""
        # Mock subscription ID
        subscription_id = uuid.uuid4()
        
        # Mock subscription model
        mock_subscription = Subscription(
            id=subscription_id,
            target_url="https://example.com/webhook",
            secret_key="test-secret",
            event_types=["order.created", "order.updated"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Setup mock behavior for execute
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_subscription
        mock_session.execute.return_value = mock_result
        
        # Call the service
        result = await subscription_service.get_subscription(subscription_id)
        
        # Check that session methods were called
        mock_session.execute.assert_called_once()
        
        # Check the returned subscription
        assert result == mock_subscription
        assert result.id == subscription_id
    
    async def test_update_subscription(self, subscription_service, mock_session):
        """Test updating a subscription."""
        # Mock subscription ID and data
        subscription_id = uuid.uuid4()
        update_data = SubscriptionUpdate(
            target_url="https://new-example.com/webhook",
            event_types=["order.created", "order.canceled"]
        )
        
        # Mock existing subscription
        mock_subscription = Subscription(
            id=subscription_id,
            target_url="https://example.com/webhook",
            secret_key="test-secret",
            event_types=["order.created", "order.updated"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Setup mock behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_subscription
        mock_session.execute.return_value = mock_result
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        # Call the service
        result = await subscription_service.update_subscription(subscription_id, update_data)
        
        # Check that session methods were called
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        
        # Check the updated subscription
        assert result.target_url == update_data.target_url
        assert result.event_types == update_data.event_types
        assert result.secret_key == mock_subscription.secret_key  # Should be unchanged
    
    async def test_delete_subscription(self, subscription_service, mock_session):
        """Test deleting a subscription."""
        # Mock subscription ID
        subscription_id = uuid.uuid4()
        
        # Mock existing subscription
        mock_subscription = Subscription(
            id=subscription_id,
            target_url="https://example.com/webhook",
            secret_key="test-secret",
            event_types=["order.created", "order.updated"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Setup mock behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_subscription
        mock_session.execute.return_value = mock_result
        mock_session.delete.return_value = None
        mock_session.commit.return_value = None
        
        # Call the service
        result = await subscription_service.delete_subscription(subscription_id)
        
        # Check that session methods were called
        mock_session.execute.assert_called_once()
        mock_session.delete.assert_called_once_with(mock_subscription)
        mock_session.commit.assert_called_once()
        
        # Check the result
        assert result is True
    
    async def test_delete_nonexistent_subscription(self, subscription_service, mock_session):
        """Test attempt to delete a subscription that doesn't exist."""
        # Mock subscription ID
        subscription_id = uuid.uuid4()
        
        # Setup mock behavior - subscription not found
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Call the service
        result = await subscription_service.delete_subscription(subscription_id)
        
        # Check that delete and commit were not called
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
        
        # Check the result
        assert result is False
