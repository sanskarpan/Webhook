"""
Subscription model definition.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import Column, DateTime, String, Table, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
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
    secret_key = Column(String(255), nullable=False)
    event_types = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Add the relationship with Webhook model
    # This is optional since the foreign key doesn't exist in the table
    # but we can uncomment it if we add the foreign key later
    # webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=True, index=True)
    # webhook = relationship("Webhook", backref="subscriptions")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<Subscription(id={self.id}, target_url={self.target_url})>"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the subscription to a dictionary."""
        return {
            "id": str(self.id),
            # "webhook_id": str(self.webhook_id) if hasattr(self, 'webhook_id') and self.webhook_id else None,
            "target_url": self.target_url,
            "secret_key": self.secret_key,
            "event_types": self.event_types,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }