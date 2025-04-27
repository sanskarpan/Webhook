#!/usr/bin/env python
"""
Test script for webhook signature verification.
This script helps debug signature verification issues by showing all the steps
in the signature generation and comparison process.
"""
import hashlib
import hmac
import json
import sys
import requests
import argparse
import uuid


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
    return f"sha256={signature}", payload_str


def test_signature_generation(payload, secret):
    """Test signature generation with detailed output."""
    print("\n=== Signature Generation Test ===")
    print(f"Secret Key: {secret}")
    
    # Calculate signature
    signature, payload_str = calculate_signature(payload, secret)
    
    print(f"\nPayload (original):")
    print(json.dumps(payload, indent=2))
    
    print(f"\nCanonical JSON string (used for signing):")
    print(payload_str)
    
    print(f"\nCalculated Signature:")
    print(signature)
    
    return signature, payload_str


def test_webhook_ingestion(base_url, subscription_id, payload, signature):
    """Test webhook ingestion with the provided signature."""
    print("\n=== Webhook Ingestion Test ===")
    print(f"Endpoint: {base_url}/ingest/{subscription_id}?event_type=order.created")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Signature header: {signature}")
    
    try:
        # Send the webhook request with signature
        response = requests.post(
            f"{base_url}/ingest/{subscription_id}?event_type=order.created",
            json=payload,
            headers={
                "X-Hub-Signature-256": signature
            }
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        try:
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response Text: {response.text}")
        
        return response
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def create_test_subscription(base_url, secret_key=None):
    """Create a new subscription for testing."""
    if not secret_key:
        secret_key = f"test-secret-{uuid.uuid4()}"
        
    subscription_data = {
        "target_url": "https://webhook.site/your-unique-id",
        "secret_key": secret_key,
        "event_types": ["order.created", "order.updated", "user.registered"]
    }
    
    print("\n=== Creating Test Subscription ===")
    print(f"Data: {json.dumps(subscription_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/subscriptions",
            json=subscription_data
        )
        
        if response.status_code != 201:
            print(f"Error creating subscription: {response.status_code}")
            print(response.text)
            return None
        
        sub_data = response.json()
        print(f"Created subscription with ID: {sub_data['id']}")
        print(f"Secret key: {sub_data['secret_key']}")
        
        return sub_data
        
    except Exception as e:
        print(f"Error creating subscription: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Test webhook signature verification')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                        help='Base URL of the webhook service')
    parser.add_argument('--subscription-id', help='Existing subscription ID to use')
    parser.add_argument('--secret-key', help='Secret key for the subscription')
    parser.add_argument('--create-subscription', action='store_true', 
                        help='Create a new subscription for testing')
    
    args = parser.parse_args()
    
    # Create subscription if requested or if no subscription ID provided
    if args.create_subscription or not args.subscription_id:
        subscription = create_test_subscription(args.base_url, args.secret_key)
        if not subscription:
            print("Failed to create subscription. Exiting.")
            sys.exit(1)
            
        subscription_id = subscription["id"]
        secret_key = subscription["secret_key"]
    else:
        subscription_id = args.subscription_id
        secret_key = args.secret_key
        
        if not secret_key:
            print("Error: Secret key is required when using an existing subscription")
            sys.exit(1)
    
    # Create a test payload
    payload = {
        "order_id": "12345",
        "customer": "John Doe",
        "amount": 99.99,
        "items": [
            {"id": "item-1", "name": "Product 1", "quantity": 2}
        ],
        "timestamp": "2023-04-28T12:30:45Z"
    }
    
    # Test signature generation
    signature, payload_str = test_signature_generation(payload, secret_key)
    
    # Test webhook ingestion
    test_webhook_ingestion(args.base_url, subscription_id, payload, signature)


if __name__ == "__main__":
    main() 