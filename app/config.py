"""
Configuration settings for the application.
"""
from typing import List, Optional
import os
import re
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file if it exists
load_dotenv()

# Function to fix Supabase URLs
def fix_database_url(url: Optional[str]) -> Optional[str]:
    """Ensure the database URL uses the asyncpg driver for SQLAlchemy async."""
    if not url:
        return None

    # If already using the asyncpg driver, return as is
    if url.startswith("postgresql+asyncpg://"):
        return url

    # Convert standard PostgreSQL URL to asyncpg
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Handle legacy Supabase URLs (postgres://)
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]

    # Otherwise, return unchanged
    return url

class Settings(BaseModel):
    """
    Application settings and configuration.
    """
    # Application Settings
    APP_NAME: str = "webhook-delivery-service"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "webhook")

    # Database
    DATABASE_URL: Optional[str] = fix_database_url(os.getenv("DATABASE_URL", None))
    SYNC_DATABASE_URL: Optional[str] = os.getenv("SYNC_DATABASE_URL", os.getenv("DATABASE_URL", None))

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", os.getenv("REDISHOST", "redis://localhost:6379/0"))
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "600"))  # 10 minutes in seconds

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # Webhook Settings
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "10"))  # seconds
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "5"))
    RETRY_DELAYS: List[int] = [int(x) for x in os.getenv("RETRY_DELAYS", "10,30,60,300,900").split(",")]  # 10s, 30s, 1m, 5m, 15m
    LOG_RETENTION_HOURS: int = int(os.getenv("LOG_RETENTION_HOURS", "72"))

    # API Documentation
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # CORS Settings
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Port configuration
    PORT: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Log application startup information
import logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)
logger.info(f"Application environment: {settings.ENVIRONMENT}")
logger.info(f"Database URL: {'configured' if settings.DATABASE_URL else 'not configured'}")
logger.info(f"Redis URL: {'configured' if settings.REDIS_URL else 'not configured'}")