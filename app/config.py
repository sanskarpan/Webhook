"""
Configuration settings for the application.
"""
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings and configuration.
    All values are loaded from environment variables.
    """
    # Application Settings
    APP_NAME: str = "webhook-delivery-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str

    # Database
    DATABASE_URL: PostgresDsn
    SYNC_DATABASE_URL: Optional[str] = None

    @validator("SYNC_DATABASE_URL", pre=True)
    def get_sync_database_url(cls, v: Optional[str], values: dict) -> str:
        """
        Convert async database URL to sync one if not provided.
        """
        if v:
            return v
        db_url = values.get("DATABASE_URL")
        assert db_url, "DATABASE_URL is required"
        
        # Convert PostgresDsn string representation to a string and replace the driver
        db_url_str = str(db_url)
        if "+asyncpg" in db_url_str:
            return db_url_str.replace("+asyncpg", "")
        return db_url_str

    # Redis
    REDIS_URL: RedisDsn
    REDIS_CACHE_TTL: int = 600  # 10 minutes in seconds

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Webhook Settings
    WEBHOOK_TIMEOUT: int = 10  # seconds
    MAX_RETRY_ATTEMPTS: int = 5
    RETRY_DELAYS: List[int] = Field(default=[10, 30, 60, 300, 900])  # 10s, 30s, 1m, 5m, 15m

    @validator("RETRY_DELAYS", pre=True)
    def parse_retry_delays(cls, v: Union[str, List[int]]) -> List[int]:
        """
        Parse retry delays from comma-separated string if provided as such.
        """
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",")]
        return v

    LOG_RETENTION_HOURS: int = 72

    # API Documentation
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # CORS Settings
    CORS_ORIGINS: List[AnyHttpUrl] = Field(default=[])

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """
        Parse CORS origins from comma-separated string if provided as such.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        """Config for env vars loading."""
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()