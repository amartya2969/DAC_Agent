"""Document model (sample resource)."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from .base import Base, BaseModel


class Document(BaseModel):
    """Document model - sample protected resource."""

    __tablename__ = 'documents'

    document_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete

    def __repr__(self):
        return f"<Document(document_id='{self.document_id}', title='{self.title}')>"

    def is_deleted(self) -> bool:
        """Check if document is soft deleted."""
        return self.deleted_at is not None
