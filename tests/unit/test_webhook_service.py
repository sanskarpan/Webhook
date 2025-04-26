"""
Unit tests for the webhook service.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.services.webhook_service import WebhookService


@pytest.fixture
def mock_delivery_log_repository():
    """Create a mock delivery log repository for testing."""
    return AsyncMock()


@pytest.fixture
def webhook_service(mock_delivery_log_repository):
    """Create a webhook service with mock repositories."""
    service = WebhookService()
    service.delivery_log_repository = mock_delivery_log_repository
    return service


class TestWebhookService:
    """Test suite for the webhook service."""
    
    async def test_get_webhook_status_success(self, webhook_service, mock_delivery_log_repository):
        """Test getting webhook status with successful delivery."""
        # Create mock webhook and delivery logs
        webhook_id = uuid.uuid4()
        subscription_id = uuid.uuid4()
        
        # Create mock delivery logs
        mock_logs = [
            MagicMock(spec=DeliveryLog, 
                      webhook_id=webhook_id,
                      subscription_id=subscription_id,
                      event_type="order.created",
                      target_url="https://example.com/webhook",
                      payload={"order_id": "12345"},
                      status=DeliveryStatus.SUCCESS,
                      http_status=200,
                      attempt_number=1,
                      error_details=None,
                      created_at=datetime.utcnow(),
                      updated_at=datetime.utcnow(),
                      next_retry_at=None)
        ]
        
        # Configure mock repository to return the logs
        mock_delivery_log_repository.get_by_webhook_id.return_value = mock_logs
        
        # Call the service method
        result = await webhook_service.get_webhook_status(webhook_id)
        
        # Check repository method was called
        mock_delivery_log_repository.get_by_webhook_id.assert_called_once_with(webhook_id)
        
        # Check response structure and values
        assert result["webhook_id"] == webhook_id
        assert result["subscription_id"] == subscription_id
        assert result["event_type"] == "order.created"
        assert result["status"] == "success"
        assert result["payload"] == {"order_id": "12345"}
        assert "updated_at" in result
        assert len(result["attempts"]) == 1
        assert result["statistics"]["total_attempts"] == 1
        assert result["statistics"]["successful"] == 1
        assert result["statistics"]["failed"] == 0
        assert result["statistics"]["pending"] == 0
        assert result["statistics"]["final_failure"] == 0
    
    async def test_get_webhook_status_multiple_attempts(self, webhook_service, mock_delivery_log_repository):
        """Test getting webhook status with multiple delivery attempts."""
        # Create mock webhook and delivery logs
        webhook_id = uuid.uuid4()
        subscription_id = uuid.uuid4()
        
        # Create base timestamp for consistent testing
        base_time = datetime.utcnow()
        
        # Create mock delivery logs with multiple attempts
        mock_logs = [
            MagicMock(spec=DeliveryLog, 
                      webhook_id=webhook_id,
                      subscription_id=subscription_id,
                      event_type="order.created",
                      target_url="https://example.com/webhook",
                      payload={"order_id": "12345"},
                      status=DeliveryStatus.FAILED_ATTEMPT,
                      http_status=500,
                      attempt_number=1,
                      error_details="Server error",
                      created_at=base_time,
                      updated_at=base_time,
                      next_retry_at=None),
            MagicMock(spec=DeliveryLog, 
                      webhook_id=webhook_id,
                      subscription_id=subscription_id,
                      event_type="order.created",
                      target_url="https://example.com/webhook",
                      payload={"order_id": "12345"},
                      status=DeliveryStatus.SUCCESS,
                      http_status=200,
                      attempt_number=2,
                      error_details=None,
                      created_at=base_time,
                      updated_at=base_time,
                      next_retry_at=None)
        ]
        
        # Configure mock repository to return the logs
        mock_delivery_log_repository.get_by_webhook_id.return_value = mock_logs
        
        # Call the service method
        result = await webhook_service.get_webhook_status(webhook_id)
        
        # Check repository method was called
        mock_delivery_log_repository.get_by_webhook_id.assert_called_once_with(webhook_id)
        
        # Check response structure and values
        assert result["webhook_id"] == webhook_id
        assert result["subscription_id"] == subscription_id
        assert result["event_type"] == "order.created"
        assert result["status"] == "success"  # Status should be from latest attempt (success)
        assert len(result["attempts"]) == 2
        assert result["attempts"][0]["attempt_number"] == 1
        assert result["attempts"][0]["status"] == "failed_attempt"
        assert result["attempts"][1]["attempt_number"] == 2
        assert result["attempts"][1]["status"] == "success"
        assert result["statistics"]["total_attempts"] == 2
        assert result["statistics"]["successful"] == 1
        assert result["statistics"]["failed"] == 1
        assert result["statistics"]["pending"] == 0
        assert result["statistics"]["final_failure"] == 0
    
    async def test_get_webhook_status_not_found(self, webhook_service, mock_delivery_log_repository):
        """Test getting webhook status for non-existent webhook."""
        # Create mock webhook ID
        webhook_id = uuid.uuid4()
        
        # Configure mock repository to return empty list (webhook not found)
        mock_delivery_log_repository.get_by_webhook_id.return_value = []
        
        # Call the service method and expect HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await webhook_service.get_webhook_status(webhook_id)
        
        # Check exception details
        assert excinfo.value.status_code == 404
        assert "Webhook not found" in excinfo.value.detail
        
        # Check repository method was called
        mock_delivery_log_repository.get_by_webhook_id.assert_called_once_with(webhook_id)
    
    async def test_get_webhook_status_error_handling(self, webhook_service, mock_delivery_log_repository):
        """Test error handling in webhook status retrieval."""
        # Create mock webhook ID
        webhook_id = uuid.uuid4()
        
        # Configure mock repository to raise an exception
        mock_delivery_log_repository.get_by_webhook_id.side_effect = Exception("Database error")
        
        # Call the service method and expect HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await webhook_service.get_webhook_status(webhook_id)
        
        # Check exception details
        assert excinfo.value.status_code == 500
        assert "Internal server error" in excinfo.value.detail
        
        # Check repository method was called
        mock_delivery_log_repository.get_by_webhook_id.assert_called_once_with(webhook_id) 