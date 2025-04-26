"""
Unit tests for the delivery service.
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.services.delivery_service import DeliveryService


@pytest.fixture
def mock_session():
    """Create a mock database session for testing."""
    mock = AsyncMock(spec=AsyncSession)
    return mock


@pytest.fixture
def delivery_service(mock_session):
    """Create a delivery service with a mock session."""
    return DeliveryService(mock_session)


class TestDeliveryService:
    """Test suite for the delivery service."""
    
    async def test_get_delivery_metrics(self, delivery_service):
        """Test getting delivery metrics."""
        # Mock metrics data
        mock_metrics = {
            "total": 150,
            "successful": 120,
            "failed": 25,
            "pending": 5,
            "final_failure": 10,
            "avg_attempts": 1.5
        }
        
        # Mock the repository's get_metrics_since method
        delivery_service.repository = AsyncMock()
        delivery_service.repository.get_metrics_since.return_value = mock_metrics
        
        # Call the service method
        result = await delivery_service.get_delivery_metrics(hours=24)
        
        # Check that repository method was called with the correct time window
        delivery_service.repository.get_metrics_since.assert_called_once()
        # Time threshold should be approximately 24 hours ago
        time_threshold_arg = delivery_service.repository.get_metrics_since.call_args[0][0]
        assert isinstance(time_threshold_arg, datetime)
        time_diff = datetime.utcnow() - time_threshold_arg
        assert 23.9 <= time_diff.total_seconds() / 3600 <= 24.1
        
        # Check the returned metrics
        assert result.total_attempts == mock_metrics["total"]
        assert result.successful == mock_metrics["successful"]
        assert result.failed == mock_metrics["failed"]
        assert result.pending == mock_metrics["pending"]
        assert result.final_failure == mock_metrics["final_failure"]
    
    async def test_update_status(self, delivery_service):
        """Test updating delivery log status."""
        # Mock log ID
        log_id = uuid.uuid4()
        
        # Mock status update
        status = DeliveryStatus.SUCCESS
        http_status = 200
        error_details = None
        
        # Mock repository method
        delivery_service.repository = AsyncMock()
        mock_log = MagicMock(spec=DeliveryLog)
        delivery_service.repository.update_status.return_value = mock_log
        
        # Call the service method
        result = await delivery_service.update_status(
            log_id=log_id,
            status=status,
            http_status=http_status,
            error_details=error_details
        )
        
        # Check that repository method was called with correct arguments
        delivery_service.repository.update_status.assert_called_once_with(
            log_id=log_id,
            status=status,
            http_status=http_status,
            error_details=error_details,
            next_retry_at=None
        )
        
        # Check the returned log
        assert result == mock_log
    
    async def test_clean_old_logs(self, delivery_service):
        """Test cleaning old logs."""
        # Mock retention hours
        retention_hours = 72
        
        # Mock repository method
        delivery_service.repository = AsyncMock()
        delivery_service.repository.clean_old_logs.return_value = 10  # 10 logs cleaned
        
        # Call the service method
        result = await delivery_service.clean_old_logs(hours=retention_hours)
        
        # Check that repository method was called
        delivery_service.repository.clean_old_logs.assert_called_once()
        
        # The threshold should be approximately retention_hours ago
        threshold_arg = delivery_service.repository.clean_old_logs.call_args[0][0]
        assert isinstance(threshold_arg, datetime)
        time_diff = datetime.utcnow() - threshold_arg
        assert 71.9 <= time_diff.total_seconds() / 3600 <= 72.1
        
        # Check the returned count
        assert result == 10
    
    async def test_create_retry_log(self, delivery_service):
        """Test creating a retry log entry."""
        # Mock previous log
        previous_log = MagicMock(spec=DeliveryLog)
        previous_log.id = uuid.uuid4()
        previous_log.webhook_id = uuid.uuid4()
        previous_log.subscription_id = uuid.uuid4()
        previous_log.target_url = "https://example.com/webhook"
        previous_log.payload = {"test": "payload"}
        previous_log.event_type = "order.created"
        previous_log.attempt_number = 1
        
        # Mock next retry time
        next_retry_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Mock repository method
        delivery_service.repository = AsyncMock()
        mock_retry_log = MagicMock(spec=DeliveryLog)
        mock_retry_log.attempt_number = 2
        delivery_service.repository.create_retry_log.return_value = mock_retry_log
        
        # Call the service method
        result = await delivery_service.create_retry_log(
            previous_log=previous_log,
            next_retry_at=next_retry_at
        )
        
        # Check that repository method was called with correct arguments
        delivery_service.repository.create_retry_log.assert_called_once_with(
            previous_log=previous_log,
            next_retry_at=next_retry_at
        )
        
        # Check the returned log
        assert result == mock_retry_log
        assert result.attempt_number == 2  # Should be incremented 