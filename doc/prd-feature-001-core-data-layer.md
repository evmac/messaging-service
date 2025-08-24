# Feature 1: Core Data Layer PRD

## Overview
Establish the foundational data models and repository layer that will be used by all other features.

## Current State
- PostgreSQL database with tables already defined in `init.sql`
- `Base` class defined in `app/database.py`
- No Pydantic models or SQLAlchemy models exist yet

## Database Schema (from init.sql)
```sql
-- Conversations table: Groups messages between participants
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table: Stores individual messages from SMS/MMS and Email providers
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    provider_type VARCHAR(20) NOT NULL CHECK (provider_type IN ('sms', 'mms', 'email')),
    provider_message_id VARCHAR(255), -- External provider's message ID
    from_address VARCHAR(255) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    attachments JSONB DEFAULT '[]', -- Array of attachment URLs
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
    message_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Participants table: Tracks who is involved in each conversation
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    address VARCHAR(255) NOT NULL, -- Phone number or email address
    address_type VARCHAR(10) NOT NULL CHECK (address_type IN ('phone', 'email')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Implementation Requirements

### 1. Pydantic Models (`app/models/`)
Create the following Pydantic models for API contracts:

**`app/models/api/messages.py`:**
```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class SendMessageRequest(BaseModel):
    from_address: str = Field(..., description="Sender address (phone or email)")
    to_address: str = Field(..., description="Recipient address (phone or email)")
    body: str = Field(..., description="Message content")
    attachments: Optional[List[str]] = Field(default=None, description="List of attachment URLs")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")

class MessageResponse(BaseModel):
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

class WebhookMessageRequest(BaseModel):
    from_address: str
    to_address: str
    body: str
    attachments: Optional[List[str]] = None
    provider_message_id: str
    timestamp: datetime
    provider_type: str  # 'sms', 'mms', 'email'
```

**`app/models/api/conversations.py`:**
```python
from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel

class ConversationResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    participants: List[str]  # List of participant addresses
    message_count: int
    last_message_timestamp: Optional[datetime]
```

**`app/models/api/participants.py`:**
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class ParticipantResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    address: str
    address_type: str  # 'phone' or 'email'
    created_at: datetime
```

### 2. SQLAlchemy Models (`app/repositories/`)
Create SQLAlchemy models that inherit from the existing `Base` class:

**`app/models/db/conversation.py`:**
```python
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")
    participants = relationship("ParticipantModel", back_populates="conversation", cascade="all, delete-orphan")
```

**`app/models/db/message.py`:**
```python
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    provider_type = Column(String(20), nullable=False)
    provider_message_id = Column(String(255))
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)
    direction = Column(String(10), nullable=False)
    status = Column(String(20), default="pending")
    message_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")
```

**`app/models/db/participant.py`:**
```python
from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class ParticipantModel(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    address = Column(String(255), nullable=False)
    address_type = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    conversation = relationship("ConversationModel", back_populates="participants")
```

### 3. Repository Classes (`app/repositories/`)
Create repository classes that handle database operations and translation:

**`app/repositories/base_repository.py`:**
```python
from typing import Generic, TypeVar, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import Base

ModelType = TypeVar('ModelType', bound=Base)
PydanticType = TypeVar('PydanticType', bound=BaseModel)

class BaseRepository(Generic[ModelType, PydanticType]):
    def __init__(self, db: AsyncSession, model_class: type[ModelType]):
        self.db = db
        self.model_class = model_class

    async def get_by_id(self, id: str) -> Optional[PydanticType]:
        query = select(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(query)
        db_model = result.scalar_one_or_none()
        return self._to_pydantic(db_model) if db_model else None

    async def create(self, pydantic_model: PydanticType) -> PydanticType:
        db_model = self._from_pydantic(pydantic_model)
        self.db.add(db_model)
        await self.db.commit()
        await self.db.refresh(db_model)
        return self._to_pydantic(db_model)

    def _to_pydantic(self, db_model: ModelType) -> PydanticType:
        """Convert SQLAlchemy model to Pydantic model"""
        raise NotImplementedError

    def _from_pydantic(self, pydantic_model: PydanticType) -> ModelType:
        """Convert Pydantic model to SQLAlchemy model"""
        raise NotImplementedError
```

**`app/repositories/conversation_repository.py`:**
```python
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.conversation import ConversationResponse
from app.repositories.base_repository import BaseRepository
from app.repositories.conversation_model import ConversationModel

class ConversationRepository(BaseRepository[ConversationModel, ConversationResponse]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ConversationModel)

    async def get_by_participants(self, participants: List[str]) -> Optional[ConversationResponse]:
        """Find conversation by participant addresses"""
        # Implementation for finding conversation by participants
        # This will be used by conversation services

    def _to_pydantic(self, db_model: ConversationModel) -> ConversationResponse:
        participants = [p.address for p in db_model.participants]
        message_count = len(db_model.messages)
        last_message = max(db_model.messages, key=lambda m: m.message_timestamp) if db_model.messages else None
        last_message_timestamp = last_message.message_timestamp if last_message else None

        return ConversationResponse(
            id=db_model.id,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            participants=participants,
            message_count=message_count,
            last_message_timestamp=last_message_timestamp
        )

    def _from_pydantic(self, pydantic_model: ConversationResponse) -> ConversationModel:
        return ConversationModel(
            id=pydantic_model.id,
            created_at=pydantic_model.created_at,
            updated_at=pydantic_model.updated_at
        )
```

## Dependencies
- None - this is the foundation layer

## Testing Requirements
- Unit tests for repository methods
- Integration tests for database operations
- Test data models with various scenarios

## Acceptance Criteria
- [ ] All Pydantic models defined and validated
- [ ] SQLAlchemy models created and properly related
- [ ] Repository classes implement CRUD operations
- [ ] Database connection and table creation verified
- [ ] Translation between Pydantic and SQLAlchemy models works correctly
