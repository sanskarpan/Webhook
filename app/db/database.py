"""
Database connection and session management.
"""
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

# Create the SQLAlchemy Base
Base = declarative_base()

# Async database setup
async_engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True
)
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Sync database setup for Celery workers
sync_engine = create_engine(
    str(settings.SYNC_DATABASE_URL),
    echo=settings.DEBUG,
    future=True
)
SyncSessionLocal = sessionmaker(
    sync_engine,
    autoflush=False,
    expire_on_commit=False
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields an async DB session.
    
    Yields:
        AsyncSession: An async SQLAlchemy session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields a sync DB session for Celery workers.
    
    Yields:
        Session: A sync SQLAlchemy session.
    """
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()