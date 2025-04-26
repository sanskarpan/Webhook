"""
End-to-end tests for the webhook delivery service.
"""
import asyncio
import json
import os
import pytest
import uuid
from httpx import AsyncClient
from typing import Dict, Any

from app.main import app
from app.db.database import Base, engine


# Setup/teardown for each test
@pytest.fixture(autouse=True)
async def setup_db():
    """Set up a clean database for each test."""
    # Drop and create all tables for tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Create a test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Mock server for receiving webhooks
class MockServer:
    def __init__(self):
        self.received_webhooks = []
        self.should_fail = False
        self.server_running = False
    
    async def handle_webhook(self, request):
        """Handle incoming webhooks in the mock server."""
        body = await request.json()
        self.received_webhooks.append({
            "headers": dict(request.headers),
            "body": body
        })
        
        if self.should_fail:
            return {"status": 500, "body": {"error": "Internal server error"}}
        else:
            return {"status": 200, "body": {"status": "success"}}
    
    async def start_server(self, port=8888):
        """Start the mock webhook server."""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/', self.handle_webhook)
        
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, 'localhost', port)
        await self.site.start()
        self.server_running = True
        print(f"Mock webhook server started on port {port}")
    
    async def stop_server(self):
        """Stop the mock webhook server."""
        if self.server_running:
            await self.runner.cleanup()
            self.server_running = False
            print("Mock webhook server stopped")


@pytest.fixture
async def mock_webhook_server():
    """Create and start a mock webhook server for testing webhook delivery."""
    server = MockServer()
    await server.start_server()
    
    yield server
    
    await server.stop_server()


# Test the complete webhook flow
@pytest.mark.asyncio
async def test_complete_webhook_flow(client, mock_webhook_server):
    """Test the complete webhook flow from creation to delivery and status checking."""
    # 1. Create a subscription
    subscription_data = {
        "target_url": "http://localhost:8888/",  # Mock server URL
        "secret_key": "test-secret",
        "event_types": ["order.created", "order.updated"]
    }
    
    response = await client.post("/subscriptions", json=subscription_data)
    assert response.status_code == 201
    
    subscription = response.json()
    subscription_id = subscription["id"]
    
    # 2. Send a webhook to be processed
    webhook_payload = {
        "order_id": "12345",
        "status": "confirmed",
        "total": 99.99
    }
    
    # Calculate a valid signature
    import hmac
    import hashlib
    signature_payload = json.dumps(webhook_payload, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        key=subscription_data["secret_key"].encode(),
        msg=signature_payload.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    response = await client.post(
        f"/ingest/{subscription_id}?event_type=order.created",
        json=webhook_payload,
        headers={"X-Hub-Signature-256": f"sha256={signature}"}
    )
    assert response.status_code == 202
    
    webhook_response = response.json()
    webhook_id = webhook_response["webhook_id"]
    
    # 3. Wait for webhook to be delivered (give enough time for async processing)
    # In real tests, you might want to implement a more robust waiting strategy
    await asyncio.sleep(2)
    
    # 4. Check if the webhook was received by the mock server
    assert len(mock_webhook_server.received_webhooks) > 0
    received = mock_webhook_server.received_webhooks[0]
    assert received["body"] == webhook_payload
    
    # 5. Check the webhook status via API
    response = await client.get(f"/status/{webhook_id}")
    assert response.status_code == 200
    
    status_data = response.json()
    assert status_data["webhook_id"] == webhook_id
    assert status_data["status"] == "success"
    assert status_data["statistics"]["successful"] > 0
    
    # 6. Check subscription delivery history
    response = await client.get(f"/subscriptions/{subscription_id}/attempts")
    assert response.status_code == 200
    
    history = response.json()
    assert history["subscription_id"] == subscription_id
    assert len(history["items"]) > 0


@pytest.mark.asyncio
async def test_webhook_delivery_retries(client, mock_webhook_server):
    """Test that webhooks are retried when delivery fails."""
    # 1. Create a subscription
    subscription_data = {
        "target_url": "http://localhost:8888/",  # Mock server URL
        "secret_key": "test-secret",
        "event_types": ["order.created"]
    }
    
    response = await client.post("/subscriptions", json=subscription_data)
    subscription_id = response.json()["id"]
    
    # 2. Configure mock server to fail delivery
    mock_webhook_server.should_fail = True
    
    # 3. Send a webhook
    webhook_payload = {"order_id": "67890", "status": "processing"}
    response = await client.post(
        f"/ingest/{subscription_id}?event_type=order.created",
        json=webhook_payload
    )
    assert response.status_code == 202
    webhook_id = response.json()["webhook_id"]
    
    # 4. Wait for initial delivery and first retry
    await asyncio.sleep(3)
    
    # 5. Check that we received more than one attempt (delivery + retry)
    assert len(mock_webhook_server.received_webhooks) > 1
    
    # 6. Check webhook status shows failed attempts
    response = await client.get(f"/status/{webhook_id}")
    assert response.status_code == 200
    
    status_data = response.json()
    assert status_data["statistics"]["failed"] > 0
    
    # Allow future attempts to succeed
    mock_webhook_server.should_fail = False
    
    # Wait for successful retry
    await asyncio.sleep(3)
    
    # Check status again to see successful attempt
    response = await client.get(f"/status/{webhook_id}")
    status_data = response.json()
    
    # Either we caught it in retry state or it eventually succeeded
    assert status_data["status"] in ["success", "pending", "failed_attempt"]


@pytest.mark.asyncio
async def test_event_type_filtering(client, mock_webhook_server):
    """Test that webhooks are only delivered for subscribed event types."""
    # 1. Create a subscription with specific event types
    subscription_data = {
        "target_url": "http://localhost:8888/",
        "secret_key": "test-secret",
        "event_types": ["order.created"]  # Only subscribe to order.created
    }
    
    response = await client.post("/subscriptions", json=subscription_data)
    subscription_id = response.json()["id"]
    
    # 2. Send webhook with allowed event type
    webhook_payload = {"order_id": "12345", "status": "created"}
    response = await client.post(
        f"/ingest/{subscription_id}?event_type=order.created",
        json=webhook_payload
    )
    assert response.status_code == 202
    
    # 3. Wait for delivery
    await asyncio.sleep(2)
    
    # 4. Verify webhook was delivered
    assert len(mock_webhook_server.received_webhooks) == 1
    
    # 5. Send webhook with non-allowed event type
    mock_webhook_server.received_webhooks = []  # Clear previous webhooks
    
    webhook_payload = {"order_id": "12345", "status": "shipped"}
    response = await client.post(
        f"/ingest/{subscription_id}?event_type=order.shipped",
        json=webhook_payload
    )
    
    # Should be rejected with 400 Bad Request
    assert response.status_code == 400
    assert "not allowed for this subscription" in response.json()["detail"]
    
    # 6. Verify no webhook was delivered
    await asyncio.sleep(2)
    assert len(mock_webhook_server.received_webhooks) == 0


@pytest.mark.asyncio
async def test_signature_verification(client, mock_webhook_server):
    """Test webhook signature verification."""
    # 1. Create a subscription with a secret
    subscription_data = {
        "target_url": "http://localhost:8888/",
        "secret_key": "very-secret-key",
        "event_types": ["payment.processed"]
    }
    
    response = await client.post("/subscriptions", json=subscription_data)
    subscription_id = response.json()["id"]
    
    # 2. Send webhook with valid signature
    webhook_payload = {"payment_id": "pay_123", "amount": 100.00, "status": "succeeded"}
    
    # Calculate signature
    import hmac
    import hashlib
    payload_string = json.dumps(webhook_payload, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        key=subscription_data["secret_key"].encode(),
        msg=payload_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Send with valid signature
    response = await client.post(
        f"/ingest/{subscription_id}?event_type=payment.processed",
        json=webhook_payload,
        headers={"X-Hub-Signature-256": f"sha256={signature}"}
    )
    assert response.status_code == 202
    
    # 3. Wait for delivery
    await asyncio.sleep(2)
    
    # 4. Verify webhook was delivered
    assert len(mock_webhook_server.received_webhooks) == 1
    
    # 5. Send webhook with invalid signature
    mock_webhook_server.received_webhooks = []  # Clear previous webhooks
    
    # Send with invalid signature
    response = await client.post(
        f"/ingest/{subscription_id}?event_type=payment.processed",
        json=webhook_payload,
        headers={"X-Hub-Signature-256": "sha256=invalid-signature"}
    )
    
    # Should be rejected with 401 Unauthorized
    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]
    
    # 6. Verify no webhook was delivered
    await asyncio.sleep(2)
    assert len(mock_webhook_server.received_webhooks) == 0 