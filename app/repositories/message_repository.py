from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.api.messages import MessageResponse
from app.models.db.message_model import MessageModel
from app.repositories.base_repository import BaseRepository


class MessageRepository(BaseRepository[MessageModel, MessageResponse]):
    """Repository for message operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, MessageModel)

    async def get_by_conversation(self, conversation_id: str) -> List[MessageResponse]:
        """Get all messages for a conversation."""
        query = (
            select(self.model_class)
            .where(self.model_class.conversation_id == UUID(conversation_id))
            .order_by(self.model_class.message_timestamp)
        )  # type: ignore
        result = await self.db.execute(query)
        db_models = result.scalars().all()
        return [self._to_pydantic(db_model) for db_model in db_models]

    async def get_by_provider_message_id(
        self, provider_message_id: str
    ) -> Optional[MessageResponse]:
        """Get message by provider message ID."""
        query = select(self.model_class).where(
            self.model_class.provider_message_id == provider_message_id
        )
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()
        return self._to_pydantic(db_model) if db_model else None

    async def get_by_status(self, status: str) -> List[MessageResponse]:
        """Get messages by status."""
        query = select(self.model_class).where(self.model_class.status == status)
        result = await self.db.execute(query)
        db_models = result.scalars().all()
        return [self._to_pydantic(db_model) for db_model in db_models]

    async def update_status(
        self, message_id: str, status: str
    ) -> Optional[MessageResponse]:
        """Update message status."""
        message = await self.get_by_id(message_id)
        if not message:
            return None

        # Create updated message with new status
        updated_data = message.model_dump()
        updated_data["status"] = status

        # Create new Pydantic model with updated data
        updated_message = MessageResponse(**updated_data)

        return await self.update(message_id, updated_message)

    def _to_pydantic(self, db_model: Any) -> MessageResponse:
        """Convert SQLAlchemy MessageModel to Pydantic MessageResponse."""
        return MessageResponse(
            id=db_model.id,
            conversation_id=db_model.conversation_id,
            provider_type=db_model.provider_type,
            provider_message_id=db_model.provider_message_id,
            from_address=db_model.from_address,
            to_address=db_model.to_address,
            body=db_model.body,
            attachments=db_model.attachments or [],
            direction=db_model.direction,
            status=db_model.status,
            message_timestamp=db_model.message_timestamp,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
        )

    def _from_pydantic(self, pydantic_model: MessageResponse) -> MessageModel:
        """Convert Pydantic MessageResponse to SQLAlchemy MessageModel."""
        return MessageModel(
            id=pydantic_model.id,
            conversation_id=pydantic_model.conversation_id,
            provider_type=pydantic_model.provider_type,
            provider_message_id=pydantic_model.provider_message_id,
            from_address=pydantic_model.from_address,
            to_address=pydantic_model.to_address,
            body=pydantic_model.body,
            attachments=pydantic_model.attachments,
            direction=pydantic_model.direction,
            status=pydantic_model.status,
            message_timestamp=pydantic_model.message_timestamp,
            created_at=pydantic_model.created_at,
            updated_at=pydantic_model.updated_at,
        )
