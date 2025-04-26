"""
Webhook model definition.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Webhook(Base):
    """Model for storing webhook configurations."""
    
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships - will be defined if needed
    # subscriptions = relationship("Subscription", back_populates="webhook")
    
    def __repr__(self) -> str:
        """String representation of the webhook."""
        return f"<Webhook {self.id}: {self.name}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the webhook to a dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 