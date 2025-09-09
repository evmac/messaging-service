from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)
PydanticType = TypeVar("PydanticType", bound=BaseModel)


class BaseRepository(Generic[ModelType, PydanticType]):
    """Generic base repository with common CRUD operations."""

    def __init__(self, db: AsyncSession, model_class: Any):
        self.db = db
        self.model_class = model_class

    async def get_by_id(self, id: str) -> Optional[PydanticType]:
        """Get a single record by ID."""
        query = select(self.model_class).where(
            self.model_class.id == UUID(id)
        )  # type: ignore
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()
        return self._to_pydantic(db_model) if db_model else None

    async def create(self, pydantic_model: PydanticType) -> PydanticType:
        """Create a new record."""
        db_model = self._from_pydantic(pydantic_model)
        self.db.add(db_model)
        await self.db.commit()
        await self.db.refresh(db_model)
        return self._to_pydantic(db_model)

    async def update(
        self, id: str, pydantic_model: PydanticType
    ) -> Optional[PydanticType]:
        """Update an existing record."""
        query = select(self.model_class).where(
            self.model_class.id == id
        )  # type: ignore
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()

        if not db_model:
            return None

        # Update fields from pydantic model
        update_data = pydantic_model.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_model, field):
                setattr(db_model, field, value)

        await self.db.commit()
        await self.db.refresh(db_model)
        return self._to_pydantic(db_model)

    async def delete(self, id: str) -> bool:
        """Delete a record by ID."""
        query = select(self.model_class).where(
            self.model_class.id == UUID(id)
        )  # type: ignore
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()

        if not db_model:
            return False

        await self.db.delete(db_model)
        await self.db.commit()
        return True

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[PydanticType]:
        """Get all records with pagination."""
        query = select(self.model_class).limit(limit).offset(offset)
        result = await self.db.execute(query)
        db_models = result.scalars().all()
        return [self._to_pydantic(db_model) for db_model in db_models]

    def _to_pydantic(self, db_model: ModelType) -> PydanticType:
        """Convert SQLAlchemy model to Pydantic model.

        This should be overridden in subclasses for specific conversion logic.
        """
        raise NotImplementedError

    def _from_pydantic(self, pydantic_model: PydanticType) -> ModelType:
        """Convert Pydantic model to SQLAlchemy model.

        This should be overridden in subclasses for specific conversion logic.
        """
        raise NotImplementedError
