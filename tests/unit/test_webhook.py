#!/usr/bin/env python
"""
Test script for webhook delivery service, demonstrating correct signature generation.
"""
import hashlib
import hmac
import json
import sys
import uuid
import requests


def calculate_signature(payload, secret):
    """Calculate HMAC-SHA256 signature for a webhook payload."""
    # Convert payload to a canonical JSON string
    payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    # Create the HMAC signature using SHA256
    signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload_str.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Return formatted signature
    return f"sha256={signature}"


def create_subscription(base_url):
    """Create a new subscription for testing."""
    subscription_data = {
        "target_url": "https://webhook.site/your-unique-id",
        "secret_key": "test-secret-key",
        "event_types": ["order.created", "user.registered"]
    }
    print(f"Creating subscription with data: {json.dumps(subscription_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/subscriptions",
            json=subscription_data
        )
        
        if response.status_code != 201:
            print(f"Error creating subscription: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        return response.json()
    except Exception as e:
        print(f"Error creating subscription: {e}")
        sys.exit(1)


def test_webhook_ingestion(base_url, subscription_id, secret_key):
    """Test webhook ingestion with proper signature."""
    # Create a test payload
    payload = {
        "order_id": "12345",
        "customer": "John Doe",
        "amount": 99.99,
        "items": [
            {"id": "item-1", "name": "Product 1", "quantity": 2}
        ]
    }
    print(f"Testing webhook with payload: {json.dumps(payload, indent=2)}")
    
    # Calculate the signature
    signature = calculate_signature(payload, secret_key)
    print(f"Calculated signature: {signature}")
    
    # Show the canonical payload string used for signing
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    print(f"Canonical payload string used for signing: {canonical_payload}")
    
    try:
        # Send the webhook request with signature
        response = requests.post(
            f"{base_url}/ingest/{subscription_id}?event_type=order.created",
            json=payload,
            headers={
                "X-Hub-Signature-256": signature
            }
        )
        
        print(f"Webhook ingestion response: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 202:
            try:
                print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
            except Exception:
                pass
    except Exception as e:
        print(f"Error testing webhook ingestion: {e}")


def main():
    base_url = "http://localhost:8000"
    
    # Create a subscription
    print("Creating subscription...")
    subscription = create_subscription(base_url)
    subscription_id = subscription["id"]
    secret_key = subscription["secret_key"]
    print(f"Created subscription with ID: {subscription_id}")
    print(f"Secret key: {secret_key}")
    
    # Test webhook ingestion
    print("\nTesting webhook ingestion...")
    test_webhook_ingestion(base_url, subscription_id, secret_key)


if __name__ == "__main__":
    main() 