"""Consent model."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from .base import Base, BaseModel
import json


class Consent(BaseModel):
    """User consent to agent access."""

    __tablename__ = 'consents'
    __table_args__ = (
        UniqueConstraint('user_id', 'client_id', name='unique_user_agent_consent'),
    )

    consent_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    client_id = Column(String, ForeignKey('agents.client_id', ondelete='CASCADE'), nullable=False, index=True)
    scopes = Column(Text, nullable=False)  # JSON array
    granted_at = Column(DateTime, nullable=False)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String, nullable=True)

    def __repr__(self):
        return f"<Consent(consent_id='{self.consent_id}', user='{self.user_id}', agent='{self.client_id}')>"

    def get_scopes(self) -> list:
        """Get scopes as a list."""
        return json.loads(self.scopes)

    def set_scopes(self, scopes: list):
        """Set scopes from a list."""
        self.scopes = json.dumps(scopes)

    def is_active(self) -> bool:
        """Check if consent is active."""
        return not self.revoked
