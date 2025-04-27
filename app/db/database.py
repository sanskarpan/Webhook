"""
Database connection and session management.
"""
import logging
import ssl
from typing import AsyncGenerator, Generator, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

# Create logger
logger = logging.getLogger(__name__)

# Create the SQLAlchemy Base
Base = declarative_base()

# Configure SSL context for secure connections
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Parse database URL to log connection details (without credentials)
def log_connection_info(url: str) -> None:
    """Log database connection information without exposing credentials."""
    if not url:
        logger.warning("No database URL provided")
        return
        
    try:
        parsed = urlparse(url)
        masked_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}"
        logger.info(f"Connecting to database: {masked_url}")
    except Exception as e:
        logger.warning(f"Could not parse database URL: {str(e)}")

# Track connection state
is_db_connected = False

# Async database setup
async_engine = None
AsyncSessionLocal = None

try:
    if settings.DATABASE_URL:
        log_connection_info(settings.DATABASE_URL)
        connect_args = {}
        
        # Add SSL for production environments and Supabase
        if settings.ENVIRONMENT != "development" or "supabase" in str(settings.DATABASE_URL).lower():
            logger.info("Using SSL for database connection")
            connect_args["ssl"] = ssl_context
        
        async_engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,  # Test connections before using them
            connect_args=connect_args
        )
        
        AsyncSessionLocal = sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        
        is_db_connected = True
        logger.info("Async database engine initialized successfully")
    else:
        logger.error("DATABASE_URL not provided, database access will be unavailable")
except Exception as e:
    logger.error(f"Failed to initialize async database engine: {str(e)}")

# Sync database setup for Celery workers
sync_engine = None
SyncSessionLocal = None

try:
    if settings.SYNC_DATABASE_URL:
        log_connection_info(settings.SYNC_DATABASE_URL)
        connect_args = {}
        
        # Add SSL for production environments and Supabase
        if settings.ENVIRONMENT != "development" or "supabase" in str(settings.SYNC_DATABASE_URL).lower():
            logger.info("Using SSL for sync database connection")
            connect_args["ssl"] = {'ca': None}  # Different format for psycopg2
        
        sync_engine = create_engine(
            str(settings.SYNC_DATABASE_URL),
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args
        )
        
        SyncSessionLocal = sessionmaker(
            sync_engine,
            autoflush=False,
            expire_on_commit=False
        )
        
        logger.info("Sync database engine initialized successfully")
    else:
        logger.warning("SYNC_DATABASE_URL not provided, sync database access will be unavailable")
except Exception as e:
    logger.error(f"Failed to initialize sync database engine: {str(e)}")


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields an async DB session.
    
    Yields:
        AsyncSession: An async SQLAlchemy session.
    """
    if not is_db_connected or not AsyncSessionLocal:
        logger.error("Database connection is not available")
        raise ConnectionError("Database connection is not available")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields a sync DB session for Celery workers.
    
    Yields:
        Session: A sync SQLAlchemy session.
    """
    if not SyncSessionLocal:
        logger.error("Sync database connection is not available")
        raise ConnectionError("Sync database connection is not available")
        
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Sync database session error: {str(e)}")
        raise
    finally:
        db.close()