"""
Main application module for the Webhook Delivery Service.
"""
import logging
import time
from typing import Dict, Any

from fastapi import FastAPI, Depends, responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.api.deps import get_delivery_service
from app.api.routes import status, subscriptions, webhooks
from app.config import settings
from app.services.delivery_service import DeliveryService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Response models for API endpoints
class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(description="Current health status of the service (healthy, degraded, unhealthy)")
    version: str = Field(description="Current version of the API")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0"
            }
        }

class MonitorMetrics(BaseModel):
    """Metrics for the last hour."""
    total_attempts: int = Field(description="Total number of webhook delivery attempts")
    successful: int = Field(description="Number of successful deliveries")
    failed: int = Field(description="Number of failed delivery attempts")
    pending: int = Field(description="Number of pending delivery attempts")
    final_failures: int = Field(description="Number of webhooks that failed all retries")
    error_rate: float = Field(description="Percentage of failed deliveries (0-100)")

    class Config:
        json_schema_extra = {
            "example": {
                "total_attempts": 150,
                "successful": 120,
                "failed": 25,
                "pending": 5,
                "final_failures": 10,
                "error_rate": 23.33
            }
        }

class MonitorResponse(BaseModel):
    """Response model for system monitor endpoint."""
    status: str = Field(description="Overall system status (healthy, degraded, overloaded)")
    version: str = Field(description="Current version of the API")
    uptime_seconds: float = Field(description="Number of seconds the system has been running")
    current_time: str = Field(description="Current server time in UTC")
    metrics: Dict[str, MonitorMetrics] = Field(description="Delivery metrics from the last hour")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 86400.5,
                "current_time": "2023-04-25 10:15:30 UTC",
                "metrics": {
                    "last_hour": {
                        "total_attempts": 150,
                        "successful": 120,
                        "failed": 25,
                        "pending": 5,
                        "final_failures": 10,
                        "error_rate": 23.33
                    }
                }
            }
        }

class RootResponse(BaseModel):
    """Response model for root endpoint."""
    name: str = Field(description="The name of the API service")
    version: str = Field(description="Current version of the API")
    docs: str = Field(description="URL path to the Swagger UI documentation")
    redoc: str = Field(description="URL path to the ReDoc documentation")
    health: str = Field(description="URL path to the health check endpoint")
    monitor: str = Field(description="URL path to the system monitoring endpoint")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Webhook Delivery Service",
                "version": "1.0.0",
                "docs": "/docs",
                "redoc": "/redoc",
                "health": "/health",
                "monitor": "/monitor"
            }
        }

# Create FastAPI application
app = FastAPI(
    title="Webhook Delivery Service",
    description="A robust webhook delivery system with automatic retries and delivery tracking",
    version="1.0.0",
    docs_url=None,  # We'll customize the docs URL
    redoc_url=None,  # We'll customize the redoc URL
)

# Set up CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(subscriptions.router)
app.include_router(webhooks.router)
app.include_router(status.router)


# Custom OpenAPI and documentation routes
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Custom Swagger UI with improved styling.
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        swagger_favicon_url="/static/favicon.ico",
        swagger_ui_parameters={
            "docExpansion": "list",
            "defaultModelsExpandDepth": 0,
            "deepLinking": True,
            "syntaxHighlight.theme": "monokai"
        }
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """
    ReDoc UI for API documentation.
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.css",
        swagger_favicon_url="/static/favicon.ico",
    )


# Custom OpenAPI schema with additional info
def custom_openapi():
    """
    Customized OpenAPI schema with additional information.
    """
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom components and security schemes if needed
    # openapi_schema["components"] = {...}
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Health check endpoint
@app.get(
    "/health", 
    tags=["monitoring"], 
    summary="Basic health check",
    response_model=HealthResponse,
    description=(
        "Simple health check endpoint for monitoring and load balancers.\n\n"
        "**Returns:**\n"
        "* Current service health status\n"
        "* API version\n\n"
        "Use this endpoint for:\n"
        "* liveness/readiness probes\n"
        "* Load balancer health checks\n"
        "* Monitoring service uptime"
    )
)
async def health_check():
    """
    Basic health check endpoint for monitoring.
    """
    return {"status": "healthy", "version": app.version}


# Root endpoint
@app.get(
    "/", 
    tags=["root"],
    response_model=RootResponse,
    summary="API information and available endpoints",
    description=(
        "Root endpoint providing basic API information and available endpoints.\n\n"
        "This endpoint returns:\n"
        "* API name and version\n"
        "* Links to documentation (Swagger UI and ReDoc)\n"
        "* Links to monitoring endpoints\n\n"
        "Use this as an entry point to discover the API capabilities."
    )
)
async def root():
    """
    Root endpoint with basic information about the API.
    """
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "monitor": "/monitor"
    }


# Add static files directory for serving images, CSS, etc.
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # No static directory available, ignore
    pass


# Store application start time
@app.on_event("startup")
async def startup_event():
    """
    Startup event handler to initialize application state.
    """
    app.state.start_time = time.time()
    logging.info(f"Application started: {app.title} v{app.version}")