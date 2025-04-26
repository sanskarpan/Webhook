"""
Integration tests for system monitoring endpoints.
"""
import pytest
from fastapi import status
from httpx import AsyncClient


class TestMonitoringEndpoints:
    """Integration test suite for system monitoring endpoints."""
    
    async def test_health_check(self, client: AsyncClient):
        """Test the health check endpoint returns correct status."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
    
    async def test_system_monitor(self, client: AsyncClient):
        """Test the detailed system monitoring endpoint returns correct data structure."""
        response = await client.get("/monitor")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check top-level fields
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "current_time" in data
        assert "metrics" in data
        
        # Check metrics structure
        metrics = data["metrics"]
        assert "last_hour" in metrics
        
        # Check last hour metrics
        last_hour = metrics["last_hour"]
        assert "total_attempts" in last_hour
        assert "successful" in last_hour
        assert "failed" in last_hour
        assert "pending" in last_hour
        assert "final_failures" in last_hour
        assert "error_rate" in last_hour
        
        # Validate types
        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["current_time"], str)
        assert isinstance(last_hour["total_attempts"], int)
        assert isinstance(last_hour["error_rate"], (int, float))
    
    async def test_root_endpoint(self, client: AsyncClient):
        """Test the root endpoint returns API info with all available endpoints."""
        response = await client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check all required links are present
        assert "name" in data
        assert "version" in data
        assert "docs" in data
        assert "redoc" in data
        assert "health" in data
        assert "monitor" in data
        
        # Validate docs endpoints
        assert data["docs"] == "/docs"
        assert data["redoc"] == "/redoc"
        assert data["health"] == "/health"
        assert data["monitor"] == "/monitor"
    
    async def test_api_docs_endpoints(self, client: AsyncClient):
        """Test the API documentation endpoints are accessible."""
        # Test Swagger UI
        response = await client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
        
        # Test ReDoc UI
        response = await client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
        
        # Test OpenAPI schema
        response = await client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]
        
        # Check schema includes our monitoring endpoints
        schema = response.json()
        assert "/health" in schema["paths"]
        assert "/monitor" in schema["paths"] 