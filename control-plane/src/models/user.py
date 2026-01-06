"""User model."""
from sqlalchemy import Column, String, Boolean, DateTime
from .base import Base, BaseModel


class User(BaseModel):
    """User account model."""

    __tablename__ = 'users'

    user_id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    last_login = Column(DateTime, nullable=True)
    account_status = Column(String, default='active', nullable=False, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String, nullable=True)

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"

    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.account_status == 'active'
