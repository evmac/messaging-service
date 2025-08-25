from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ParticipantResponse(BaseModel):
    """Response model for participant data."""

    id: UUID
    conversation_id: UUID
    address: str
    address_type: str  # 'phone' or 'email'
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
