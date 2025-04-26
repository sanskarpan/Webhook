"""
Subscription model definition.
"""
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Column, DateTime, String, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from app.db.database import Base


class Subscription(Base):
    """
    Model representing a webhook subscription.
    
    A subscription defines a target URL where webhook payloads should be delivered
    and optional configuration like secret key and allowed event types.
    """
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    target_url = Column(String(255), nullable=False, index=True)
    secret_key = Column(String(255), nullable=True)
    event_types = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<Subscription(id={self.id}, target_url={self.target_url})>"