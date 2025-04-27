"""
Tests for webhook signature validation functionality.
"""
import json
import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock, AsyncMock

from app.api.deps import validate_webhook_signature


@pytest.fixture
def mock_subscription_service():
    """Create a mock subscription service."""
    mock_service = AsyncMock()
    mock_service.get.return_value = MagicMock(
        id="test-subscription-id",
        secret_key="test-secret",
        target_url="https://example.com/webhook",
        event_types=["order.created", "order.updated"]
    )
    return mock_service


@pytest.fixture
def generate_valid_signature():
    """Generate a valid signature for testing."""
    import hmac
    import hashlib
    
    def _generate(payload, secret_key):
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            key=secret_key.encode(),
            msg=payload_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    return _generate


class TestWebhookSignatureValidation:
    """Test suite for webhook signature validation."""
    
    async def test_valid_signature(self, mock_subscription_service, generate_valid_signature):
        """Test with a valid signature."""
        # Test data
        subscription_id = "test-subscription-id"
        payload = {"order_id": "12345", "amount": 100.00}
        event_type = "order.created"
        
        # Generate valid signature
        signature_header = generate_valid_signature(payload, "test-secret")
        
        # Call the validation function with patched service
        with patch('app.api.deps.get_subscription_service', return_value=mock_subscription_service):
            # Should pass without raising an exception
            result = await validate_webhook_signature(
                subscription_id=subscription_id,
                event_type=event_type,
                signature_header=signature_header,
                payload=payload
            )
        
        # Should return the subscription
        assert result.id == subscription_id
        assert "test-secret" in result.secret_key
    
    async def test_missing_signature(self, mock_subscription_service):
        """Test with a missing signature header."""
        # Test data
        subscription_id = "test-subscription-id"
        payload = {"order_id": "12345", "amount": 100.00}
        event_type = "order.created"
        
        # Call the validation function with patched service
        with patch('app.api.deps.get_subscription_service', return_value=mock_subscription_service):
            # Should raise an HTTPException
            with pytest.raises(HTTPException) as excinfo:
                await validate_webhook_signature(
                    subscription_id=subscription_id,
                    event_type=event_type,
                    signature_header=None,  # Missing signature
                    payload=payload
                )
        
        # Check the exception details
        assert excinfo.value.status_code == 401
        assert "missing" in excinfo.value.detail.lower()
    
    async def test_invalid_signature_format(self, mock_subscription_service):
        """Test with an invalid signature format."""
        # Test data
        subscription_id = "test-subscription-id"
        payload = {"order_id": "12345", "amount": 100.00}
        event_type = "order.created"
        
        # Invalid signature formats
        invalid_signatures = [
            "invalid-format", 
            "sha256:", 
            "sha512=abc123",
            "something=else"
        ]
        
        # Call the validation function with patched service
        with patch('app.api.deps.get_subscription_service', return_value=mock_subscription_service):
            for sig in invalid_signatures:
                # Should raise an HTTPException
                with pytest.raises(HTTPException) as excinfo:
                    await validate_webhook_signature(
                        subscription_id=subscription_id,
                        event_type=event_type,
                        signature_header=sig,
                        payload=payload
                    )
                
                # Check the exception details
                assert excinfo.value.status_code == 401
                assert "invalid" in excinfo.value.detail.lower()
    
    async def test_invalid_signature_value(self, mock_subscription_service):
        """Test with an invalid signature value."""
        # Test data
        subscription_id = "test-subscription-id"
        payload = {"order_id": "12345", "amount": 100.00}
        event_type = "order.created"
        
        # Invalid signature value
        invalid_signature = "sha256=abc123def456"
        
        # Call the validation function with patched service
        with patch('app.api.deps.get_subscription_service', return_value=mock_subscription_service):
            # Should raise an HTTPException
            with pytest.raises(HTTPException) as excinfo:
                await validate_webhook_signature(
                    subscription_id=subscription_id,
                    event_type=event_type,
                    signature_header=invalid_signature,
                    payload=payload
                )
        
        # Check the exception details
        assert excinfo.value.status_code == 401
        assert "mismatch" in excinfo.value.detail.lower()
    
    async def test_subscription_not_found(self):
        """Test when subscription is not found."""
        # Test data
        subscription_id = "nonexistent-id"
        payload = {"order_id": "12345", "amount": 100.00}
        event_type = "order.created"
        signature_header = "sha256=abc123"
        
        # Mock subscription service that raises an exception
        mock_service = AsyncMock()
        mock_service.get.side_effect = HTTPException(status_code=404, detail="Subscription not found")
        
        # Call the validation function with patched service
        with patch('app.api.deps.get_subscription_service', return_value=mock_service):
            # Should raise an HTTPException
            with pytest.raises(HTTPException) as excinfo:
                await validate_webhook_signature(
                    subscription_id=subscription_id,
                    event_type=event_type,
                    signature_header=signature_header,
                    payload=payload
                )
        
        # Check the exception details
        assert excinfo.value.status_code == 404
        assert "not found" in excinfo.value.detail.lower()
    
    async def test_unsupported_event_type(self, mock_subscription_service):
        """Test with an unsupported event type."""
        # Test data
        subscription_id = "test-subscription-id"
        payload = {"order_id": "12345", "amount": 100.00}
        event_type = "unsupported.event"  # Not in the subscription's event_types
        
        # Generate a valid signature
        import hmac
        import hashlib
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            key="test-secret".encode(),
            msg=payload_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={signature}"
        
        # Call the validation function with patched service
        with patch('app.api.deps.get_subscription_service', return_value=mock_subscription_service):
            # Should raise an HTTPException
            with pytest.raises(HTTPException) as excinfo:
                await validate_webhook_signature(
                    subscription_id=subscription_id,
                    event_type=event_type,
                    signature_header=signature_header,
                    payload=payload
                )
        
        # Check the exception details
        assert excinfo.value.status_code == 400
        assert "event type" in excinfo.value.detail.lower() 