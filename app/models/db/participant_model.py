import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ParticipantModel(Base):
    """SQLAlchemy model for participants table."""

    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    address = Column(String(255), nullable=False)
    address_type = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    conversation = relationship("ConversationModel", back_populates="participants")

    # Constraints (enforced by database CHECK constraints in init.sql)
    # address_type IN ('phone', 'email')
