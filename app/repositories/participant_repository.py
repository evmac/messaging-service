import uuid
from datetime import datetime
from typing import Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.api.participants import ParticipantResponse
from app.models.db.participant_model import ParticipantModel
from app.repositories.base_repository import BaseRepository


class ParticipantRepository(BaseRepository[ParticipantModel, ParticipantResponse]):
    """Repository for participant operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ParticipantModel)

    async def get_by_conversation(
        self, conversation_id: str
    ) -> List[ParticipantResponse]:
        """Get all participants for a conversation."""
        query = select(self.model_class).where(
            self.model_class.conversation_id == UUID(conversation_id)
        )  # type: ignore
        result = await self.db.execute(query)
        db_models = result.scalars().all()
        return [self._to_pydantic(db_model) for db_model in db_models]

    async def get_by_address(self, address: str) -> List[ParticipantResponse]:
        """Get all conversations where an address is a participant."""
        query = select(self.model_class).where(self.model_class.address == address)
        result = await self.db.execute(query)
        db_models = result.scalars().all()
        return [self._to_pydantic(db_model) for db_model in db_models]

    async def add_participant(
        self, conversation_id: str, address: str, address_type: str
    ) -> ParticipantResponse:
        """Add a participant to a conversation."""
        # Check if participant already exists
        query = select(self.model_class).where(
            self.model_class.conversation_id == conversation_id,
            self.model_class.address == address,
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            return self._to_pydantic(existing)

        # Create new participant
        new_participant = ParticipantResponse(
            id=uuid.uuid4(),
            conversation_id=UUID(conversation_id),
            address=address,
            address_type=address_type,
            created_at=datetime.utcnow(),
        )

        return await self.create(new_participant)

    def _to_pydantic(self, db_model: Any) -> ParticipantResponse:
        """Convert SQLAlchemy ParticipantModel to Pydantic ParticipantResponse."""
        return ParticipantResponse(
            id=db_model.id,
            conversation_id=db_model.conversation_id,
            address=db_model.address,
            address_type=db_model.address_type,
            created_at=db_model.created_at,
        )

    def _from_pydantic(self, pydantic_model: ParticipantResponse) -> ParticipantModel:
        """Convert Pydantic ParticipantResponse to SQLAlchemy ParticipantModel."""
        return ParticipantModel(
            id=pydantic_model.id,
            conversation_id=pydantic_model.conversation_id,
            address=pydantic_model.address,
            address_type=pydantic_model.address_type,
            created_at=pydantic_model.created_at,
        )
