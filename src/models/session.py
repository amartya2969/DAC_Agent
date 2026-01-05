"""Session model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from .base import Base, BaseModel


class Session(BaseModel):
    """User session model."""

    __tablename__ = 'sessions'

    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    session_data = Column(Text, nullable=True)  # JSON session data
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Session(session_id='{self.session_id[:8]}...', user='{self.user_id}')>"

    def is_valid(self) -> bool:
        """Check if session is still valid."""
        from datetime import datetime
        return datetime.utcnow() < self.expires_at
