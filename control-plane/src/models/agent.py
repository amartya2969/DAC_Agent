"""Agent model."""
from sqlalchemy import Column, String, ForeignKey, Text
from .base import Base, BaseModel
import json


class Agent(BaseModel):
    """Agent client application model."""

    __tablename__ = 'agents'

    client_id = Column(String, primary_key=True)
    client_secret_hash = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    homepage_url = Column(String, nullable=True)
    privacy_policy_url = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    redirect_uris = Column(Text, nullable=False)  # JSON array
    allowed_scopes = Column(Text, nullable=False)  # JSON array
    agent_type = Column(String, default='confidential', nullable=False)
    status = Column(String, default='active', nullable=False, index=True)
    created_by = Column(String, ForeignKey('users.user_id'), nullable=True)

    def __repr__(self):
        return f"<Agent(client_id='{self.client_id}', name='{self.agent_name}')>"

    def get_redirect_uris(self) -> list:
        """Get redirect URIs as a list."""
        return json.loads(self.redirect_uris)

    def set_redirect_uris(self, uris: list):
        """Set redirect URIs from a list."""
        self.redirect_uris = json.dumps(uris)

    def get_allowed_scopes(self) -> list:
        """Get allowed scopes as a list."""
        return json.loads(self.allowed_scopes)

    def set_allowed_scopes(self, scopes: list):
        """Set allowed scopes from a list."""
        self.allowed_scopes = json.dumps(scopes)

    def is_active(self) -> bool:
        """Check if agent is active."""
        return self.status == 'active'
