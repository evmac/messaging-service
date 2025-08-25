import uuid

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ConversationModel(Base):
    """SQLAlchemy model for conversations table."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    messages = relationship(
        "MessageModel", back_populates="conversation", cascade="all, delete-orphan"
    )
    participants = relationship(
        "ParticipantModel", back_populates="conversation", cascade="all, delete-orphan"
    )
