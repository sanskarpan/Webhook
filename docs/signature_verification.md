# Webhook Signature Verification

This document explains how webhook signatures are generated and verified in the Webhook Delivery Service.

## Overview

Webhook signatures are used to verify that the webhook payload was sent by an authorized sender and hasn't been tampered with. The system uses HMAC-SHA256 signatures for this purpose.

## How Signatures Are Generated

When a webhook is sent to the `/ingest/{subscription_id}` endpoint, the system expects a signature header that is calculated as follows:

1. The payload is converted to a canonical JSON string using:
   ```python
   json.dumps(payload, sort_keys=True, separators=(',', ':'))
   ```
   This ensures that the same string is always produced for the same data, regardless of whitespace or key order.

2. An HMAC-SHA256 hash is calculated using the subscription's secret key:
   ```python
   signature = hmac.new(
       key=secret_key.encode('utf-8'),
       msg=canonical_payload.encode('utf-8'),
       digestmod=hashlib.sha256
   ).hexdigest()
   ```

3. The signature is sent in the `X-Hub-Signature-256` header with the format:
   ```
   X-Hub-Signature-256: sha256=<hexadecimal_hash>
   ```

## Example in Python

```python
import hashlib
import hmac
import json
import requests

# Your webhook payload
payload = {
    "order_id": "12345",
    "customer": "John Doe",
    "amount": 99.99
}

# Secret key from your subscription
secret_key = "your-subscription-secret-key"

# Convert to canonical form
canonical_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))

# Calculate signature
signature = hmac.new(
    key=secret_key.encode('utf-8'),
    msg=canonical_payload.encode('utf-8'),
    digestmod=hashlib.sha256
).hexdigest()

# Format as header value
signature_header = f"sha256={signature}"

# Send the webhook
response = requests.post(
    "https://example.com/ingest/your-subscription-id",
    json=payload,
    headers={"X-Hub-Signature-256": signature_header}
)
```

## Example in JavaScript (Node.js)

```javascript
const crypto = require('crypto');
const axios = require('axios');

// Your webhook payload
const payload = {
    order_id: '12345',
    customer: 'John Doe',
    amount: 99.99
};

// Secret key from your subscription
const secretKey = 'your-subscription-secret-key';

// Convert to canonical form
const canonicalPayload = JSON.stringify(payload, Object.keys(payload).sort(), ',');

// Calculate signature
const signature = crypto
    .createHmac('sha256', secretKey)
    .update(canonicalPayload)
    .digest('hex');

// Format as header value
const signatureHeader = `sha256=${signature}`;

// Send the webhook
axios.post('https://example.com/ingest/your-subscription-id', payload, {
    headers: {
        'X-Hub-Signature-256': signatureHeader
    }
})
.then(response => console.log('Webhook sent:', response.status))
.catch(error => console.error('Error sending webhook:', error));
```

## Testing Signature Verification

We provide several tools to help test the signature verification mechanism:

1. **test_webhook_ingestion.py**: A comprehensive script for testing webhook ingestion with proper signatures.
   ```
   python test_webhook_ingestion.py --complete-test
   ```

2. **test_signature.py**: A focused script for testing and debugging signature generation and validation.
   ```
   python test_signature.py
   ```

3. **generate_signature.py**: A simple script to generate signatures for a given payload and secret key.
   ```
   python generate_signature.py
   ```

## Common Issues

If you're experiencing issues with signature verification, check the following:

1. **Key Order**: Make sure you're sorting the keys in your JSON payload before signing
2. **Whitespace**: Remove all unnecessary whitespace in your JSON
3. **Secret Key**: Verify that you're using the correct secret key from your subscription
4. **Header Format**: The header must be in the format `sha256=<hexadecimal_hash>`
5. **Encoding**: Both the payload and secret key must be UTF-8 encoded before hashing

## Debugging

When a signature verification fails, the API responds with a 401 Unauthorized status code and includes debugging information in the response:

```json
{
  "error": "Invalid signature",
  "detail": {
    "error": "Invalid signature",
    "detail": "The provided signature does not match the expected signature",
    "debug_info": {
      "received": "sha256=1234567890abcdef",
      "note": "Signatures are calculated using canonical JSON representation with sorted keys"
    }
  }
}
```

This information can help you identify what went wrong in your signature calculation. 