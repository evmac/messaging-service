from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.api.conversations import ConversationResponse
from app.models.db.conversation_model import ConversationModel
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
        # This will require joining with participants table
        # For now, return None - this will be implemented when we have the
        # full participant relationship
        return None

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
