from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.api.conversations import ConversationResponse
from app.models.db.conversation_model import ConversationModel
from app.models.db.participant_model import ParticipantModel
from app.repositories.base_repository import BaseRepository


class ConversationRepository(BaseRepository[ConversationModel, ConversationResponse]):
    """Repository for conversation operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ConversationModel)

    async def get_by_id(self, id: str) -> Optional[ConversationResponse]:
        """Get a conversation by ID with participants and messages loaded."""
        query = (
            select(self.model_class)
            .where(self.model_class.id == UUID(id))
            .options(
                selectinload(self.model_class.messages),
                selectinload(self.model_class.participants),
            )
        )  # type: ignore
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()
        return self._to_pydantic(db_model) if db_model else None

    async def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> List[ConversationResponse]:
        """Get all conversations with participants and messages loaded."""
        query = (
            select(self.model_class)
            .options(
                selectinload(self.model_class.messages),
                selectinload(self.model_class.participants),
            )
            .limit(limit)
            .offset(offset)
        )  # type: ignore
        result = await self.db.execute(query)
        db_models = result.scalars().all()
        return [self._to_pydantic(db_model) for db_model in db_models]

    async def get_by_participants(
        self, participants: List[str]
    ) -> Optional[ConversationResponse]:
        """Find conversation by participant addresses."""
        # Sort participants to ensure consistent ordering for matching
        sorted_participants = sorted(participants)

        # Query for conversations that have exactly these participants
        # Simplified approach - production might need more sophisticated matching
        for participant_address in sorted_participants:
            # Find conversations where this participant exists
            query = (
                select(self.model_class)
                .join(self.model_class.participants)
                .where(self.model_class.participants.any(address=participant_address))
                .options(
                    selectinload(self.model_class.messages),
                    selectinload(self.model_class.participants),
                )
            )  # type: ignore
            result = await self.db.execute(query)
            conversations = result.scalars().all()

            # Check each conversation to see if it has exactly the same participants
            for conversation in conversations:
                conversation_participants = sorted(
                    [p.address for p in conversation.participants]
                )
                if conversation_participants == sorted_participants:
                    return self._to_pydantic(conversation)

        return None

    async def create_empty(self) -> ConversationResponse:
        """Create a new empty conversation."""
        empty_conversation = ConversationResponse(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=[],
            message_count=0,
            last_message_timestamp=None,
        )

        return await self.create(empty_conversation)

    async def create(
        self, pydantic_model: ConversationResponse
    ) -> ConversationResponse:
        """Create a new conversation."""
        db_model = self._from_pydantic(pydantic_model)
        self.db.add(db_model)
        await self.db.commit()
        await self.db.refresh(db_model)

        # After creating, we need to eagerly load relationships for _to_pydantic
        query = (
            select(self.model_class)
            .where(self.model_class.id == db_model.id)
            .options(
                selectinload(self.model_class.messages),
                selectinload(self.model_class.participants),
            )
        )  # type: ignore
        result = await self.db.execute(query)
        refreshed_db_model = result.scalar_one_or_none()
        return (
            self._to_pydantic(refreshed_db_model)
            if refreshed_db_model
            else pydantic_model
        )

    async def get_with_messages(
        self, conversation_id: str
    ) -> Optional[ConversationResponse]:
        """Get conversation with all messages loaded."""
        query = (
            select(self.model_class)
            .where(self.model_class.id == UUID(conversation_id))
            .options(
                selectinload(self.model_class.messages),
                selectinload(self.model_class.participants),
            )
        )  # type: ignore
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()
        return self._to_pydantic(db_model) if db_model else None

    async def list_conversations(
        self,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        participant_address: Optional[str] = None,
    ) -> List[ConversationResponse]:
        """List conversations with optional filtering."""

        # Use simpler approach that works with existing _to_pydantic method
        # The existing method handles message count and last message timestamp
        query = select(self.model_class).options(
            selectinload(self.model_class.messages),
            selectinload(self.model_class.participants),
        )

        # Filter by participant if provided
        if participant_address:
            query = query.join(self.model_class.participants).where(
                ParticipantModel.address == participant_address
            )

        # Order by created_at for now (we can improve this later)
        query = query.order_by(self.model_class.created_at.desc())

        # Apply pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        result = await self.db.execute(query)
        db_models = result.scalars().all()

        return [self._to_pydantic(db_model) for db_model in db_models]

    def _to_pydantic(self, db_model: Any) -> ConversationResponse:
        """Convert SQLAlchemy ConversationModel to Pydantic ConversationResponse."""
        participants = [p.address for p in db_model.participants]
        message_count = len(db_model.messages)
        last_message = (
            max(db_model.messages, key=lambda m: m.message_timestamp)
            if db_model.messages
            else None
        )
        last_message_timestamp = (
            last_message.message_timestamp if last_message else None
        )

        return ConversationResponse(
            id=db_model.id,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            participants=participants,
            message_count=message_count,
            last_message_timestamp=last_message_timestamp,
        )

    def _from_pydantic(self, pydantic_model: ConversationResponse) -> ConversationModel:
        """Convert Pydantic ConversationResponse to SQLAlchemy ConversationModel."""
        return ConversationModel(
            id=pydantic_model.id,
            created_at=pydantic_model.created_at,
            updated_at=pydantic_model.updated_at,
        )
