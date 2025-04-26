"""
Configuration settings for the application.
"""
from typing import List
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class Settings(BaseModel):
    """
    Application settings and configuration with hardcoded values.
    """
    # Application Settings
    APP_NAME: str = "webhook-delivery-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "webhook"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL")
    REDIS_CACHE_TTL: int = 600  # 10 minutes in seconds

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND")

    # Webhook Settings
    WEBHOOK_TIMEOUT: int = 10  # seconds
    MAX_RETRY_ATTEMPTS: int = 5
    RETRY_DELAYS: List[int] = [10, 30, 60, 300, 900]  # 10s, 30s, 1m, 5m, 15m
    LOG_RETENTION_HOURS: int = 72

    # API Documentation
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # CORS Settings
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS").split(",")


# Create settings instance
settings = Settings()