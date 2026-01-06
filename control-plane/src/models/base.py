"""Base database model and utilities."""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime
from datetime import datetime
import uuid

Base = declarative_base()


class BaseModel(Base):
    """Abstract base model with common fields."""

    __abstract__ = True

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    @staticmethod
    def generate_id(prefix: str) -> str:
        """Generate a unique ID with a prefix.

        Args:
            prefix: Prefix for the ID (e.g., 'user', 'agent', 'token')

        Returns:
            Unique identifier string like 'user_abc123xyz'
        """
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
