"""
Tests for Redis cache functionality.
"""
import json
import pytest
from unittest.mock import patch, AsyncMock

from app.cache.redis_cache import RedisCache


class TestRedisCache:
    """Test suite for Redis cache operations."""
    
    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create a Redis cache with mocked Redis instance for testing."""
        with patch('app.cache.redis_cache.get_redis', return_value=mock_redis):
            cache = RedisCache()
            cache.redis = mock_redis
            return cache
    
    async def test_get_nonexistent_key(self, redis_cache):
        """Test retrieving a nonexistent key from the cache."""
        # Try to get a non-existent key
        result = await redis_cache.get("nonexistent_key")
        
        # Should return None for non-existent keys
        assert result is None
    
    async def test_set_and_get(self, redis_cache):
        """Test setting and retrieving a value."""
        # Set a value in the cache
        key = "test_key"
        value = {"id": "123", "name": "Test Value"}
        
        # Store in cache with a TTL
        await redis_cache.set(key, value, ttl=60)
        
        # Retrieve the value
        result = await redis_cache.get(key)
        
        # Should return the correct value
        assert result == value
    
    async def test_delete(self, redis_cache):
        """Test deleting a value from the cache."""
        # Set a value in the cache
        key = "delete_key"
        value = {"id": "456", "name": "Value to Delete"}
        
        # Store in cache
        await redis_cache.set(key, value)
        
        # Verify it's there
        assert await redis_cache.get(key) == value
        
        # Delete it
        await redis_cache.delete(key)
        
        # Verify it's gone
        assert await redis_cache.get(key) is None
    
    async def test_set_with_custom_ttl(self, redis_cache, mock_redis):
        """Test setting a value with a custom TTL."""
        # Set a spy on the redis set method
        mock_redis.set = AsyncMock(wraps=mock_redis.set)
        
        # Set a value with a custom TTL
        key = "ttl_key"
        value = "ttl_value"
        custom_ttl = 120
        
        await redis_cache.set(key, value, ttl=custom_ttl)
        
        # Verify the TTL was passed correctly
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == custom_ttl
        
        # Verify the value is set
        assert await redis_cache.get(key) == value
    
    async def test_complex_object(self, redis_cache):
        """Test setting and retrieving a complex object."""
        # Create a complex nested structure
        complex_value = {
            "id": "789",
            "name": "Complex Object",
            "nested": {
                "list": [1, 2, 3, 4],
                "dict": {"a": 1, "b": 2},
                "null_value": None,
                "bool_value": True
            }
        }
        
        key = "complex_key"
        
        # Store and retrieve
        await redis_cache.set(key, complex_value)
        result = await redis_cache.get(key)
        
        # Should preserve all structure
        assert result == complex_value 