"""Audit log model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from .base import Base, BaseModel


class AuditLog(BaseModel):
    """Audit log model for security events."""

    __tablename__ = 'audit_logs'

    log_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True, index=True)
    client_id = Column(String, ForeignKey('agents.client_id', ondelete='SET NULL'), nullable=True, index=True)
    resource = Column(String, nullable=True)
    action = Column(String, nullable=False)
    result = Column(String, nullable=False, index=True)  # success, failure, error
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    event_metadata = Column(Text, nullable=True)  # JSON additional metadata

    def __repr__(self):
        return f"<AuditLog(event='{self.event_type}', result='{self.result}')>"
