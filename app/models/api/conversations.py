from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationResponse(BaseModel):
    """Response model for conversation data."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    participants: List[str]  # List of participant addresses
    message_count: int
    last_message_timestamp: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
