"""Scope model."""
from sqlalchemy import Column, String, Boolean, Text
from .base import Base, BaseModel


class Scope(BaseModel):
    """Scope definition model."""

    __tablename__ = 'scopes'

    scope_id = Column(String, primary_key=True)
    scope_name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False, index=True)
    sensitive = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Scope(name='{self.scope_name}', category='{self.category}')>"
