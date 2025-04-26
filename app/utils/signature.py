"""
Utilities for webhook signature verification.
"""
import hashlib
import hmac
import json
from typing import Any, Dict, Optional


def calculate_signature(payload: Dict[str, Any], secret: str) -> str:
    """
    Calculate HMAC-SHA256 signature for a webhook payload.
    
    Args:
        payload: The webhook payload to sign
        secret: The secret key used for signing
        
    Returns:
        Hex-encoded signature string with "sha256=" prefix
    """
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


def verify_signature(
    payload: Dict[str, Any],
    secret: str,
    signature: Optional[str]
) -> bool:
    """
    Verify a webhook signature against a payload and secret.
    
    Args:
        payload: The webhook payload
        secret: The secret key used for signing
        signature: The provided signature to verify
        
    Returns:
        True if signature is valid, False otherwise
    """
    if signature is None:
        return False
    
    # Calculate the expected signature
    expected_signature = calculate_signature(payload, secret)
    
    # Use constant-time comparison to avoid timing attacks
    return hmac.compare_digest(expected_signature, signature)


def parse_signature_header(signature_header: Optional[str]) -> Optional[str]:
    """
    Parse the X-Hub-Signature-256 header to extract the signature.
    
    Args:
        signature_header: The raw signature header value
        
    Returns:
        Parsed signature or None if invalid
    """
    if not signature_header:
        return None
    
    # The header should be in the format "sha256=<hex_signature>"
    if not signature_header.startswith("sha256="):
        return None
    
    return signature_header