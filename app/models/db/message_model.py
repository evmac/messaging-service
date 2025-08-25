import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MessageModel(Base):
    """SQLAlchemy model for messages table."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    provider_type = Column(String(20), nullable=False)
    provider_message_id = Column(String(255))
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)
    direction = Column(String(10), nullable=False)
    status = Column(String(20), default="pending")
    message_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")

    # Constraints (enforced by database CHECK constraints in init.sql)
    # provider_type IN ('sms', 'mms', 'email')
    # direction IN ('inbound', 'outbound')
    # status IN ('pending', 'sent', 'delivered', 'failed')
