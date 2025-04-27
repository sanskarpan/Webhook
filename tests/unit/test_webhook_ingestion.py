#!/usr/bin/env python
"""
Comprehensive test script for webhook ingestion with signature verification.
This script helps test the webhook ingestion endpoint by:
1. Creating a test subscription
2. Generating proper signatures for payloads
3. Sending test webhooks with correct signatures
4. Providing detailed debugging information
"""
import argparse
import hashlib
import hmac
import json
import sys
import uuid
from typing import Dict, Any, Optional
import requests


class WebhookTester:
    """Class for testing webhook ingestion with signature verification."""
    
    def __init__(self, base_url: str):
        """Initialize the webhook tester."""
        self.base_url = base_url.rstrip('/')
        self.subscription = None
        
    def create_subscription(self, target_url: Optional[str] = None, secret_key: Optional[str] = None) -> Dict[str, Any]:
        """Create a new subscription for testing."""
        if not target_url:
            target_url = "https://webhook.site/your-unique-id"
            
        if not secret_key:
            secret_key = f"test-secret-{uuid.uuid4()}"
            
        subscription_data = {
            "target_url": target_url,
            "secret_key": secret_key,
            "event_types": ["order.created", "order.updated", "user.registered"]
        }
        
        print("\n=== Creating Test Subscription ===")
        print(f"Data: {json.dumps(subscription_data, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/subscriptions",
                json=subscription_data
            )
            
            if response.status_code != 201:
                print(f"Error creating subscription: {response.status_code}")
                print(response.text)
                return None
            
            self.subscription = response.json()
            print(f"Created subscription with ID: {self.subscription['id']}")
            print(f"Secret key: {self.subscription['secret_key']}")
            print(f"Event types: {', '.join(self.subscription['event_types'])}")
            print(f"Target URL: {self.subscription['target_url']}")
            
            return self.subscription
            
        except Exception as e:
            print(f"Error creating subscription: {e}")
            return None
            
    def calculate_signature(self, payload: Dict[str, Any], secret: str) -> str:
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
            
    def send_test_webhook(self, 
                          payload: Dict[str, Any], 
                          event_type: str, 
                          subscription_id: Optional[str] = None,
                          secret_key: Optional[str] = None) -> Dict[str, Any]:
        """Send a test webhook with proper signature."""
        if not subscription_id and not self.subscription:
            print("Error: No subscription available. Create a subscription first.")
            return None
            
        subscription_id = subscription_id or self.subscription["id"]
        secret_key = secret_key or self.subscription["secret_key"]
        
        print("\n=== Sending Test Webhook ===")
        print(f"Subscription ID: {subscription_id}")
        print(f"Event type: {event_type}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Calculate signature
        signature, canonical_payload = self.calculate_signature(payload, secret_key)
        print(f"\nCanonical payload string (used for signing): {canonical_payload}")
        print(f"Calculated signature: {signature}")
        
        # Prepare request
        url = f"{self.base_url}/ingest/{subscription_id}"
        if event_type:
            url += f"?event_type={event_type}"
            
        headers = {
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json"
        }
        
        print(f"\nSending request to: {url}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            print(f"\nResponse status code: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"Response body: {json.dumps(response_data, indent=2)}")
                return response_data
            except:
                print(f"Response text: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error sending webhook: {e}")
            return None
            
    def run_complete_test(self, event_type: str = "order.created"):
        """Run a complete test of the webhook ingestion flow."""
        # 1. Create a subscription if not already created
        if not self.subscription:
            if not self.create_subscription():
                print("Failed to create subscription. Exiting.")
                return
                
        # 2. Create a test payload
        payload = {
            "order_id": str(uuid.uuid4()),
            "customer": "Test Customer",
            "amount": 123.45,
            "items": [
                {"id": "item-1", "name": "Test Product", "quantity": 1, "price": 123.45}
            ],
            "timestamp": "2023-05-01T12:00:00Z"
        }
        
        # 3. Send the webhook
        result = self.send_test_webhook(payload, event_type)
        
        if result:
            print("\n=== Test Completed Successfully ===")
            print(f"Webhook ID: {result.get('webhook_id')}")
            print("You can check the webhook delivery status using:")
            print(f"  GET {self.base_url}/status/{result.get('webhook_id')}")
        else:
            print("\n=== Test Failed ===")
            print("Check the error messages above for details.")
            

def main():
    """Run the webhook tester."""
    parser = argparse.ArgumentParser(description='Test webhook ingestion with signature verification')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                        help='Base URL of the webhook service')
    parser.add_argument('--create-subscription', action='store_true',
                        help='Create a new subscription for testing')
    parser.add_argument('--target-url', 
                        help='Target URL for the subscription')
    parser.add_argument('--secret-key',
                        help='Secret key for the subscription')
    parser.add_argument('--subscription-id',
                        help='Existing subscription ID to use')
    parser.add_argument('--event-type', default='order.created',
                        help='Event type for the webhook')
    parser.add_argument('--payload-file',
                        help='JSON file containing the webhook payload')
    parser.add_argument('--complete-test', action='store_true',
                        help='Run a complete test (create subscription and send webhook)')
                        
    args = parser.parse_args()
    
    # Initialize the webhook tester
    tester = WebhookTester(args.base_url)
    
    # Run the appropriate action based on arguments
    if args.complete_test:
        tester.run_complete_test(args.event_type)
        return
        
    if args.create_subscription:
        subscription = tester.create_subscription(args.target_url, args.secret_key)
        if not subscription:
            print("Failed to create subscription. Exiting.")
            sys.exit(1)
            
    # If we have a payload file, send a webhook
    if args.payload_file:
        try:
            with open(args.payload_file, 'r') as f:
                payload = json.load(f)
        except Exception as e:
            print(f"Error loading payload file: {e}")
            sys.exit(1)
            
        subscription_id = args.subscription_id or (tester.subscription and tester.subscription["id"])
        secret_key = args.secret_key or (tester.subscription and tester.subscription["secret_key"])
        
        if not subscription_id or not secret_key:
            print("Error: Either --subscription-id and --secret-key must be provided, or use --create-subscription first")
            sys.exit(1)
            
        tester.send_test_webhook(payload, args.event_type, subscription_id, secret_key)
    elif not args.create_subscription:
        # If no specific action was requested, print help
        parser.print_help()
    

if __name__ == "__main__":
    main() 