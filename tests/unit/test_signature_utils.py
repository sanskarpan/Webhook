"""
Unit tests for signature verification utilities.
"""
import json

import pytest

from app.utils.signature import calculate_signature, parse_signature_header, verify_signature


class TestSignatureUtils:
    """Test suite for webhook signature utilities."""
    
    def test_calculate_signature(self):
        """Test HMAC-SHA256 signature calculation."""
        # Test payload
        payload = {
            "order_id": "12345",
            "status": "confirmed",
            "total": 99.99
        }
        
        # Test secret
        secret = "test-secret-key"
        
        # Calculate signature
        signature = calculate_signature(payload, secret)
        
        # Verify the signature format
        assert signature.startswith("sha256=")
        assert len(signature) > 10  # Should have a reasonable length
        
        # Calculate expected signature manually for comparison
        import hashlib
        import hmac
        
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        expected_hash = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload_str.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare with our function's output
        assert signature == f"sha256={expected_hash}"
    
    def test_verify_signature_valid(self):
        """Test that valid signatures are verified correctly."""
        # Test payload
        payload = {
            "order_id": "12345",
            "status": "confirmed"
        }
        
        # Test secret
        secret = "test-secret-key"
        
        # Calculate a valid signature
        signature = calculate_signature(payload, secret)
        
        # Verify the signature
        assert verify_signature(payload, secret, signature) is True
    
    def test_verify_signature_invalid(self):
        """Test that invalid signatures are rejected."""
        # Test payload
        payload = {
            "order_id": "12345",
            "status": "confirmed"
        }
        
        # Test secret
        secret = "test-secret-key"
        
        # Invalid signature
        invalid_signature = "sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        # Verify the signature
        assert verify_signature(payload, secret, invalid_signature) is False
    
    def test_verify_signature_missing(self):
        """Test that missing signatures are rejected."""
        # Test payload
        payload = {
            "order_id": "12345",
            "status": "confirmed"
        }
        
        # Test secret
        secret = "test-secret-key"
        
        # Verify with None signature
        assert verify_signature(payload, secret, None) is False
    
    def test_parse_signature_header_valid(self):
        """Test parsing a valid signature header."""
        # Valid header
        header = "sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        
        # Parse the header
        parsed = parse_signature_header(header)
        
        # Should return the header unchanged
        assert parsed == header
    
    def test_parse_signature_header_invalid_format(self):
        """Test parsing an invalid signature header format."""
        # Invalid header format
        header = "invalid-0123456789abcdef"
        
        # Parse the header
        parsed = parse_signature_header(header)
        
        # Should return None for invalid format
        assert parsed is None
    
    def test_parse_signature_header_missing(self):
        """Test parsing a missing signature header."""
        # Parse None header
        parsed = parse_signature_header(None)
        
        # Should return None
        assert parsed is None