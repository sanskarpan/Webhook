"""
Integration tests for the full webhook flow (ingestion to delivery).
"""
import json
import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.delivery_log import DeliveryStatus
from app.models.subscription import Subscription
from app.utils.signature import calculate_signature


class TestWebhookFlow:
    """Integration test suite for the webhook delivery flow."""
    
    async def test_webhook_ingestion_flow(self, client: AsyncClient, test_subscription: Subscription, db_session):
        """Test the full webhook ingestion flow."""
        # Create test payload
        payload = {
            "order_id": "12345",
            "status": "confirmed",
            "total": 99.99
        }
        
        # Create signature
        signature = calculate_signature(payload, test_subscription.secret_key)
        
        # Test ingestion endpoint
        with patch('app.workers.delivery_worker.process_webhook_delivery.delay') as mock_task:
            response = await client.post(
                f"/ingest/{test_subscription.id}",
                json=payload,
                headers={
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json"
                },
                params={"event_type": "order.created"}
            )
            
            # Check response
            assert response.status_code == status.HTTP_202_ACCEPTED
            response_data = response.json()
            assert "webhook_id" in response_data
            assert response_data["subscription_id"] == str(test_subscription.id)
            assert response_data["event_type"] == "order.created"
            
            # Check that the task was queued
            mock_task.assert_called_once()
            assert len(mock_task.call_args[0]) == 1  # One argument (delivery_log_id)
            
            # Check that a delivery log was created
            webhook_id = uuid.UUID(response_data["webhook_id"])
            query = "SELECT * FROM delivery_logs WHERE webhook_id = :webhook_id"
            result = await db_session.execute(query, {"webhook_id": webhook_id})
            log = result.mappings().first()
            
            assert log is not None
            assert log["subscription_id"] == test_subscription.id
            assert log["event_type"] == "order.created"
            assert log["status"] == "pending"
            assert log["attempt_number"] == 1
            assert json.loads(log["payload"]) == payload
    
    async def test_webhook_status_endpoint(self, client: AsyncClient, test_subscription: Subscription, db_session):
        """Test the webhook status endpoint."""
        # Create a delivery log directly in the database
        webhook_id = uuid.uuid4()
        query = """
        INSERT INTO delivery_logs (
            id, webhook_id, subscription_id, target_url, payload, event_type, 
            attempt_number, status, http_status, error_details, created_at
        ) VALUES (
            :id, :webhook_id, :subscription_id, :target_url, :payload, :event_type,
            :attempt_number, :status, :http_status, :error_details, CURRENT_TIMESTAMP
        )
        """
        
        await db_session.execute(
            query,
            {
                "id": uuid.uuid4(),
                "webhook_id": webhook_id,
                "subscription_id": test_subscription.id,
                "target_url": test_subscription.target_url,
                "payload": json.dumps({"test": "payload"}),
                "event_type": "order.created",
                "attempt_number": 1,
                "status": DeliveryStatus.SUCCESS.value,
                "http_status": 200,
                "error_details": None
            }
        )
        await db_session.commit()
        
        # Test status endpoint
        response = await client.get(f"/status/{webhook_id}")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        status_data = response.json()
        
        assert status_data["webhook_id"] == str(webhook_id)
        assert status_data["subscription_id"] == str(test_subscription.id)
        assert status_data["event_type"] == "order.created"
        assert status_data["status"] == "success"
        assert len(status_data["attempts"]) == 1
        assert status_data["attempts"][0]["http_status"] == 200
    
    async def test_subscription_attempts_endpoint(self, client: AsyncClient, test_subscription: Subscription, db_session):
        """Test the subscription attempts endpoint."""
        # Create multiple delivery logs for this subscription
        for i in range(3):
            webhook_id = uuid.uuid4()
            query = """
            INSERT INTO delivery_logs (
                id, webhook_id, subscription_id, target_url, payload, event_type, 
                attempt_number, status, http_status, error_details, created_at
            ) VALUES (
                :id, :webhook_id, :subscription_id, :target_url, :payload, :event_type,
                :attempt_number, :status, :http_status, :error_details, CURRENT_TIMESTAMP
            )
            """
            
            await db_session.execute(
                query,
                {
                    "id": uuid.uuid4(),
                    "webhook_id": webhook_id,
                    "subscription_id": test_subscription.id,
                    "target_url": test_subscription.target_url,
                    "payload": json.dumps({"test": f"payload-{i}"}),
                    "event_type": f"order.event{i}",
                    "attempt_number": 1,
                    "status": DeliveryStatus.SUCCESS.value,
                    "http_status": 200,
                    "error_details": None
                }
            )
        await db_session.commit()
        
        # Test subscription attempts endpoint
        response = await client.get(f"/subscriptions/{test_subscription.id}/attempts?limit=10")
        
        # Check response
        assert response.status_code == status.HTTP_200_OK
        attempts_data = response.json()
        
        assert attempts_data["subscription_id"] == str(test_subscription.id)
        assert len(attempts_data["items"]) == 3
        assert attempts_data["total"] == 3