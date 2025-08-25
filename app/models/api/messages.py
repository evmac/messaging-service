from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""

    from_address: str = Field(..., description="Sender address (phone or email)")
    to_address: str = Field(..., description="Recipient address (phone or email)")
    body: str = Field(..., description="Message content")
    attachments: Optional[List[str]] = Field(
        default=None, description="List of attachment URLs"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Message timestamp",
    )


class MessageResponse(BaseModel):
    """Response model for message data."""

    id: UUID
    conversation_id: UUID
    provider_type: str  # 'sms', 'mms', 'email'
    provider_message_id: Optional[str]
    from_address: str
    to_address: str
    body: str
    attachments: List[str]
    direction: str  # 'inbound' or 'outbound'
    status: str  # 'pending', 'sent', 'delivered', 'failed'
    message_timestamp: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookMessageRequest(BaseModel):
    """Request model for webhook message processing."""

    from_address: str
    to_address: str
    body: str
    attachments: Optional[List[str]] = None
    provider_message_id: str
    timestamp: datetime
    provider_type: str  # 'sms', 'mms', 'email'
