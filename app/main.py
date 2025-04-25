"""
Main application module for the Webhook Delivery Service.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import WebhookServiceException
from app.db.init_db import create_tables, dispose_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    logger.info("Application startup in progress")
    # Create DB tables on startup
    await create_tables()
    logger.info("Database tables created successfully")
    
    yield
    
    logger.info("Application shutdown in progress")
    # Clean up database connections
    await dispose_db()
    logger.info("Database connections disposed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="A robust webhook delivery service that ingests, queues, and delivers webhooks with retry capabilities",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_url=f"{settings.api_root_path}/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for custom exceptions
@app.exception_handler(WebhookServiceException)
async def webhook_service_exception_handler(
    request: Request, exc: WebhookServiceException
) -> JSONResponse:
    """
    Handle custom webhook service exceptions.
    
    Args:
        request: The incoming request
        exc: The exception that was raised
        
    Returns:
        A JSON response with the error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the service is running.
    
    Returns:
        Dictionary with status information
    """
    return {"status": "healthy", "service": settings.app_name}


# Include API router
app.include_router(api_router, prefix=settings.api_root_path)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )