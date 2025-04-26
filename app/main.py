"""
Main application module for the Webhook Delivery Service.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app.api.routes import status, subscriptions, webhooks
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

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
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {"status": "healthy", "version": app.version}


# Root endpoint
@app.get("/", tags=["root"])
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
    }


# Add static files directory for serving images, CSS, etc.
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # No static directory available, ignore
    pass