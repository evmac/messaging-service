from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.messages import MessageResponse
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository


class GetConversationMessagesService:
    """Service for retrieving messages from a specific conversation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
        direction: Optional[str] = None,
    ) -> List[MessageResponse]:
        """
        Get messages for a specific conversation:

        1. Verify conversation exists
        2. Retrieve messages from database with pagination and filtering
        3. Return formatted responses
        """
        # Validate parameters
        if limit is not None and (limit <= 0 or limit > 1000):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 1000"
            )
        if offset is not None and offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be non-negative")
        if direction is not None and direction not in ["inbound", "outbound"]:
            raise HTTPException(
                status_code=400,
                detail="Direction must be 'inbound', 'outbound', or None",
            )

        # Use default values if None
        limit = limit or 100
        offset = offset or 0

        # Step 1: Verify conversation exists
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Step 2: Get messages from repository
        messages = await self.message_repo.get_by_conversation_id(
            conversation_id=UUID(conversation_id),
            limit=limit,
            offset=offset,
            direction=direction,
        )

        # Step 3: Transform to response format (already handled by repository)
        return messages

    async def get_message_details(self, message_id: str) -> MessageResponse:
        """Get detailed information about a specific message"""
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        return message
