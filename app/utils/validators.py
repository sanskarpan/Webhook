"""
Validation utilities for the webhook service.
"""
import re
from typing import List, Optional


def validate_event_type(event_type: str) -> bool:
    """
    Validate an event type string.
    
    Args:
        event_type: Event type string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not event_type:
        return False
    
    # Event types should follow the pattern: resource.action
    # Example: order.created, user.updated, etc.
    pattern = r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$'
    return bool(re.match(pattern, event_type))


def validate_url(url: str) -> bool:
    """
    Validate a URL string.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    # Basic URL validation pattern
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_secret_key(secret_key: Optional[str]) -> bool:
    """
    Validate a secret key.
    
    Args:
        secret_key: Secret key to validate
        
    Returns:
        True if valid, False otherwise
    """
    if secret_key is None:
        return True  # Optional
    
    # Secret key should be at least 16 characters for security
    if len(secret_key) < 16:
        return False
    
    # Should contain a mix of characters for better security
    has_lowercase = bool(re.search(r'[a-z]', secret_key))
    has_uppercase = bool(re.search(r'[A-Z]', secret_key))
    has_digit = bool(re.search(r'[0-9]', secret_key))
    has_special = bool(re.search(r'[^a-zA-Z0-9]', secret_key))
    
    # Require at least 3 of the 4 character types
    char_type_count = sum([has_lowercase, has_uppercase, has_digit, has_special])
    return char_type_count >= 3


def validate_event_types(event_types: Optional[List[str]]) -> bool:
    """
    Validate a list of event types.
    
    Args:
        event_types: List of event types to validate
        
    Returns:
        True if all are valid, False otherwise
    """
    if event_types is None:
        return True  # Optional
    
    if not isinstance(event_types, list):
        return False
    
    if not event_types:
        return False  # Empty list is invalid
    
    # Check each event type
    return all(validate_event_type(event) for event in event_types)