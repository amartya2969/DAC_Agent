"""Token models for authorization codes, access tokens, and refresh tokens."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from .base import Base, BaseModel
import json


class AuthorizationCode(BaseModel):
    """Authorization code model."""

    __tablename__ = 'authorization_codes'

    code = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey('agents.client_id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    redirect_uri = Column(String, nullable=False)
    scopes = Column(Text, nullable=False)  # JSON array
    code_challenge = Column(String, nullable=True)
    code_challenge_method = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AuthorizationCode(code='{self.code[:8]}...', client='{self.client_id}')>"

    def get_scopes(self) -> list:
        """Get scopes as a list."""
        return json.loads(self.scopes)

    def set_scopes(self, scopes: list):
        """Set scopes from a list."""
        self.scopes = json.dumps(scopes)

    def is_valid(self) -> bool:
        """Check if authorization code is still valid."""
        from datetime import datetime
        return not self.used and datetime.utcnow() < self.expires_at


class AccessToken(BaseModel):
    """Access token model."""

    __tablename__ = 'access_tokens'

    jti = Column(String, primary_key=True)  # JWT ID
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    client_id = Column(String, ForeignKey('agents.client_id', ondelete='CASCADE'), nullable=False, index=True)
    scopes = Column(Text, nullable=False)  # JSON array
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String, nullable=True)

    def __repr__(self):
        return f"<AccessToken(jti='{self.jti[:8]}...', user='{self.user_id}')>"

    def get_scopes(self) -> list:
        """Get scopes as a list."""
        return json.loads(self.scopes)

    def set_scopes(self, scopes: list):
        """Set scopes from a list."""
        self.scopes = json.dumps(scopes)

    def is_valid(self) -> bool:
        """Check if access token is still valid."""
        from datetime import datetime
        return not self.revoked and datetime.utcnow() < self.expires_at


class RefreshToken(BaseModel):
    """Refresh token model."""

    __tablename__ = 'refresh_tokens'

    token_id = Column(String, primary_key=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    client_id = Column(String, ForeignKey('agents.client_id', ondelete='CASCADE'), nullable=False, index=True)
    access_token_jti = Column(String, ForeignKey('access_tokens.jti', ondelete='SET NULL'), nullable=True)
    scopes = Column(Text, nullable=False)  # JSON array
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String, nullable=True)
    replaced_by = Column(String, ForeignKey('refresh_tokens.token_id', ondelete='SET NULL'), nullable=True)

    def __repr__(self):
        return f"<RefreshToken(token_id='{self.token_id[:8]}...', user='{self.user_id}')>"

    def get_scopes(self) -> list:
        """Get scopes as a list."""
        return json.loads(self.scopes)

    def set_scopes(self, scopes: list):
        """Set scopes from a list."""
        self.scopes = json.dumps(scopes)

    def is_valid(self) -> bool:
        """Check if refresh token is still valid."""
        from datetime import datetime
        return not self.revoked and datetime.utcnow() < self.expires_at
