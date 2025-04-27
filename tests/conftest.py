"""
Common fixtures for testing the webhook delivery service.
"""
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, List, Optional

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app
from app.config import settings
from app.models.subscription import Subscription
from app.models.webhook import Webhook
from app.models.delivery_log import DeliveryLog, DeliveryStatus

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create async session for tests
TestingSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Setup the database dependency for testing
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for testing."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Get a test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True, scope="function")
async def setup_db():
    """Set up a clean database for each test."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def webhook_payload() -> Dict[str, Any]:
    """Get a sample webhook payload for testing."""
    return {
        "order_id": "12345",
        "customer": "Test Customer",
        "amount": 123.45,
        "items": [
            {"id": "item-1", "name": "Test Product", "quantity": 1, "price": 123.45}
        ],
        "timestamp": "2023-05-01T12:00:00Z"
    }


@pytest.fixture
def subscription_data() -> Dict[str, Any]:
    """Get sample subscription data for testing."""
    return {
        "target_url": "https://example.com/webhook",
        "secret_key": "test-secret-key",
        "event_types": ["order.created", "order.updated"]
    }


@pytest.fixture
def calculate_signature():
    """Get a function to calculate signature for testing."""
    from app.utils.signature import calculate_signature as calc_sig
    return calc_sig


@pytest.fixture
def generate_signature():
    """Return a function to generate a webhook signature."""
    def _generate_signature(payload: Dict[str, Any], secret_key: str) -> str:
        import hmac
        import hashlib
        
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            key=secret_key.encode(),
            msg=payload_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    return _generate_signature


@pytest.fixture
async def test_subscription(db_session) -> Subscription:
    """Create a test subscription in the database."""
    # Create a subscription directly in the database
    subscription_id = uuid.uuid4()
    subscription = Subscription(
        id=subscription_id,
        target_url="https://example.com/webhook",
        secret_key="test-secret-key",
        event_types=["order.created", "order.updated", "user.registered"],
        active=True
    )
    
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    
    return subscription


@pytest.fixture
async def create_webhook(db_session):
    """Create a test webhook with optional delivery logs."""
    async def _create_webhook(
        subscription_id: uuid.UUID,
        event_type: str = "order.created",
        payload: Optional[Dict[str, Any]] = None,
        status: DeliveryStatus = DeliveryStatus.PENDING,
        delivery_logs: int = 0
    ) -> Webhook:
        if payload is None:
            payload = {
                "order_id": str(uuid.uuid4()),
                "amount": 100.00,
                "status": "created"
            }
        
        webhook = Webhook(
            id=uuid.uuid4(),
            subscription_id=subscription_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.utcnow()
        )
        
        db_session.add(webhook)
        await db_session.commit()
        await db_session.refresh(webhook)
        
        # Create delivery logs if requested
        if delivery_logs > 0:
            for i in range(1, delivery_logs + 1):
                log_status = status
                if i < delivery_logs:
                    log_status = DeliveryStatus.FAILED_ATTEMPT
                
                log = DeliveryLog(
                    id=uuid.uuid4(),
                    webhook_id=webhook.id,
                    subscription_id=subscription_id,
                    event_type=event_type,
                    target_url="https://example.com/webhook",
                    payload=payload,
                    attempt_number=i,
                    status=log_status,
                    http_status=200 if log_status == DeliveryStatus.SUCCESS else 500,
                    error_details=None if log_status == DeliveryStatus.SUCCESS else "Test error",
                    created_at=datetime.utcnow() - timedelta(minutes=delivery_logs - i),
                    updated_at=datetime.utcnow() - timedelta(minutes=delivery_logs - i),
                    next_retry_at=None if log_status != DeliveryStatus.FAILED_ATTEMPT else datetime.utcnow() + timedelta(minutes=i)
                )
                db_session.add(log)
            
            await db_session.commit()
        
        return webhook
    
    return _create_webhook


@pytest.fixture
async def mock_redis():
    """Mock Redis for testing."""
    class MockRedis:
        def __init__(self):
            self.data = {}
            self.expires = {}
        
        async def get(self, key):
            return self.data.get(key)
        
        async def set(self, key, value, ex=None):
            self.data[key] = value
            if ex:
                self.expires[key] = datetime.utcnow() + timedelta(seconds=ex)
        
        async def delete(self, key):
            if key in self.data:
                del self.data[key]
                if key in self.expires:
                    del self.expires[key]
    
    return MockRedis()
