"""
Redis cache implementation for storing subscription details.
"""
import json
from typing import Any, Dict, Optional, Type, TypeVar, Union

import redis
from pydantic import BaseModel

from app.config import settings

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

# Initialize Redis connection
redis_client = redis.from_url(str(settings.REDIS_URL), decode_responses=True)


class RedisCache:
    """Redis cache client for storing and retrieving data with TTL."""

    @staticmethod
    def _format_key(key: str, prefix: Optional[str] = None) -> str:
        """
        Format a cache key with an optional prefix.
        
        Args:
            key: Base key to format
            prefix: Optional prefix to prepend
            
        Returns:
            Formatted cache key string
        """
        if prefix:
            return f"{prefix}:{key}"
        return key

    @staticmethod
    def set(
        key: str,
        value: Union[str, Dict[str, Any], BaseModel],
        expire: int = settings.REDIS_CACHE_TTL,
        prefix: Optional[str] = None
    ) -> bool:
        """
        Set a value in the cache with optional expiration.
        
        Args:
            key: Cache key
            value: Value to store (string, dict, or Pydantic model)
            expire: Expiration time in seconds
            prefix: Optional key prefix
            
        Returns:
            True if successful, False otherwise
        """
        formatted_key = RedisCache._format_key(key, prefix)
        
        # Convert Pydantic models to dict
        if isinstance(value, BaseModel):
            value = value.model_dump()
            
        # Serialize dict/model to JSON string
        if isinstance(value, dict):
            value = json.dumps(value)
            
        return redis_client.set(formatted_key, value, ex=expire)
    
    @staticmethod
    def get(key: str, prefix: Optional[str] = None) -> Optional[str]:
        """
        Get a string value from the cache.
        
        Args:
            key: Cache key to retrieve
            prefix: Optional key prefix
            
        Returns:
            String value or None if not found
        """
        formatted_key = RedisCache._format_key(key, prefix)
        return redis_client.get(formatted_key)
    
    @staticmethod
    def get_json(key: str, prefix: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a JSON value from the cache and parse it.
        
        Args:
            key: Cache key to retrieve
            prefix: Optional key prefix
            
        Returns:
            Dictionary or None if not found/invalid
        """
        value = RedisCache.get(key, prefix)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    @staticmethod
    def get_model(key: str, model_cls: Type[T], prefix: Optional[str] = None) -> Optional[T]:
        """
        Get a JSON value and convert to a Pydantic model.
        
        Args:
            key: Cache key to retrieve
            model_cls: Pydantic model class to parse into
            prefix: Optional key prefix
            
        Returns:
            Instantiated model or None if not found/invalid
        """
        data = RedisCache.get_json(key, prefix)
        if data:
            try:
                return model_cls.model_validate(data)
            except Exception:
                return None
        return None
    
    @staticmethod
    def delete(key: str, prefix: Optional[str] = None) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: Cache key to delete
            prefix: Optional key prefix
            
        Returns:
            True if key was deleted, False otherwise
        """
        formatted_key = RedisCache._format_key(key, prefix)
        return bool(redis_client.delete(formatted_key))
    
    @staticmethod
    def exists(key: str, prefix: Optional[str] = None) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key to check
            prefix: Optional key prefix
            
        Returns:
            True if key exists, False otherwise
        """
        formatted_key = RedisCache._format_key(key, prefix)
        return bool(redis_client.exists(formatted_key))