"""
Redis cache implementation for storing subscription details.
"""
import json
import logging
import os
from typing import Any, Dict, Optional, Type, TypeVar, Union

import redis
import ssl
from pydantic import BaseModel
from redis.exceptions import RedisError

from app.config import settings

# Setup logging
logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

# Initialize Redis connection
REDIS_AVAILABLE = False
redis_client = None

try:
    # Get Redis URL from environment variable or settings
    redis_url = os.environ.get("REDIS_URL", settings.REDIS_URL)
    
    # Log the Redis connection attempt (without exposing credentials)
    parsed_url = redis_url.split('@')
    masked_url = parsed_url[-1] if len(parsed_url) > 1 else redis_url
    logger.info(f"Attempting to connect to Redis at: ...@{masked_url}")
    
    # Initialize connection
    if redis_url:
        # Use TLS for Upstash or rediss:// schemes
        connect_kwargs = {"decode_responses": True, "socket_connect_timeout": 1, "socket_timeout": 1}
        if 'upstash.io' in redis_url or redis_url.startswith('rediss://'):
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            connect_kwargs["ssl_context"] = ssl_ctx
        # Initialize Redis client with short timeouts (no blocking ping)
        redis_client = redis.from_url(redis_url, **connect_kwargs)
        REDIS_AVAILABLE = True
        logger.info("Redis client initialized; caching enabled")
    else:
        logger.warning("No Redis URL provided. Caching will be disabled.")
except Exception as e:
    logger.warning(f"Redis connection failed: {str(e)}. Caching will be disabled.")


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
        if not REDIS_AVAILABLE or not redis_client:
            return False
            
        try:
            formatted_key = RedisCache._format_key(key, prefix)
            
            # Convert Pydantic models to dict
            if isinstance(value, BaseModel):
                value = value.model_dump()
                
            # Serialize dict/model to JSON string
            if isinstance(value, dict):
                value = json.dumps(value)
                
            return redis_client.set(formatted_key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {str(e)}")
            return False
    
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
        if not REDIS_AVAILABLE or not redis_client:
            return None
            
        try:
            formatted_key = RedisCache._format_key(key, prefix)
            return redis_client.get(formatted_key)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return None
    
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
        if not REDIS_AVAILABLE or not redis_client:
            return None
            
        try:
            value = RedisCache.get(key, prefix)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
            return None
        except Exception as e:
            logger.error(f"Redis get_json error for key {key}: {str(e)}")
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
        if not REDIS_AVAILABLE or not redis_client:
            return None
            
        try:
            data = RedisCache.get_json(key, prefix)
            if data:
                try:
                    return model_cls.model_validate(data)
                except Exception:
                    return None
            return None
        except Exception as e:
            logger.error(f"Redis get_model error for key {key}: {str(e)}")
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
        if not REDIS_AVAILABLE or not redis_client:
            return False
            
        try:
            formatted_key = RedisCache._format_key(key, prefix)
            return bool(redis_client.delete(formatted_key))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {str(e)}")
            return False
    
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
        if not REDIS_AVAILABLE or not redis_client:
            return False
            
        try:
            formatted_key = RedisCache._format_key(key, prefix)
            return bool(redis_client.exists(formatted_key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {str(e)}")
            return False