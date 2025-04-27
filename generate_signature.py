import hmac
import hashlib
import json

# Your webhook payload 
payload = {
  "created_at": "2023-04-25T10:15:30Z",
  "customer_id": "CUST-6789",
  "items": [
    {
      "price": 29.99,
      "product_id": "PROD-101",
      "quantity": 2
    },
    {
      "price": 49.99,
      "product_id": "PROD-205",
      "quantity": 1
    }
  ],
  "order_id": "ORD-12345",
  "status": "confirmed",
  "total": 109.97
}

# The secret key from your subscription
# secret_key = "your-secret-key-for-signing"
secret_key = "updated-secret-key"


payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))

# Create the HMAC signature using SHA256
signature = hmac.new(
    key=secret_key.encode("utf-8"), 
    msg=payload_str.encode("utf-8"), 
    digestmod=hashlib.sha256
).hexdigest()

print(f"Payload: {json.dumps(payload, indent=2)}")
print(f"Canonical JSON string used for signing: {payload_str}")
print(f"X-Hub-Signature-256: sha256={signature}")
