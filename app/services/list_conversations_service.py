from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.conversations import ConversationResponse
from app.repositories.conversation_repository import ConversationRepository


class ListConversationsService:
    """Service for listing conversations with filtering and pagination."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)

    async def list_conversations(
        self,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        participant_address: Optional[str] = None,
    ) -> List[ConversationResponse]:
        """
        List conversations with optional filtering:

        1. Retrieve conversations from database
        2. Apply filters if provided
        3. Return formatted responses
        """
        # Validate parameters
        if limit is not None and (limit <= 0 or limit > 1000):
            raise ValueError("Limit must be between 1 and 1000")
        if offset is not None and offset < 0:
            raise ValueError("Offset must be non-negative")

        # Use default values if None
        limit = limit or 50
        offset = offset or 0

        # Step 1: Get conversations from repository
        conversations = await self.conversation_repo.list_conversations(
            limit=limit, offset=offset, participant_address=participant_address
        )

        # Step 2: Transform to response format (already handled by repository)
        return conversations

    async def get_conversation_summary(
        self, conversation_id: str
    ) -> ConversationResponse:
        """Get detailed information about a specific conversation"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation with ID {conversation_id} not found")
        return conversation
