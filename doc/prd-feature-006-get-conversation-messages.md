# Feature 6: Get Conversation Messages PRD

## Overview
Implement functionality to retrieve all messages for a specific conversation.

## Dependencies
- Feature 1: Core Data Layer (Pydantic models, repositories)

## API Endpoint (from test script)
```
GET /api/conversations/{id}/messages
```

## Expected Response Format
Based on the test script, the endpoint should return a list of messages for the specified conversation.

## Implementation Requirements

### 1. Service Layer (`app/services/`)

**`app/services/get_conversation_messages_service.py`:**
```python
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.message import MessageResponse
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository

class GetConversationMessagesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0,
        direction: Optional[str] = None  # 'inbound', 'outbound', or None for both
    ) -> List[MessageResponse]:
        """
        Get messages for a specific conversation:
        1. Verify conversation exists
        2. Retrieve messages from database
        3. Apply filters if provided
        4. Return formatted responses
        """

        # Step 1: Verify conversation exists
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Step 2: Get messages from repository
        messages = await self.message_repo.get_by_conversation_id(
            conversation_id=UUID(conversation_id),
            limit=limit,
            offset=offset,
            direction=direction
        )

        # Step 3: Transform to response format
        return messages

    async def get_message_details(self, message_id: str) -> MessageResponse:
        """Get detailed information about a specific message"""
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        return message
```

### 2. Router Layer (`app/routers/`)

**`app/routers/conversations.py` (add to existing file):**
```python
from typing import List, Optional
from fastapi import Query
from app.services.get_conversation_messages_service import GetConversationMessagesService

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: Optional[int] = Query(100, description="Maximum number of messages to return"),
    offset: Optional[int] = Query(0, description="Number of messages to skip"),
    direction: Optional[str] = Query(None, description="Filter by message direction ('inbound', 'outbound')"),
    db: AsyncSession = Depends(get_db)
) -> List[MessageResponse]:
    """
    Get all messages for a specific conversation.

    Query parameters:
    - limit: Maximum number of messages to return (default: 100)
    - offset: Number of messages to skip (default: 0)
    - direction: Filter messages by direction ('inbound', 'outbound')
    """
    service = GetConversationMessagesService(db)
    return await service.get_conversation_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        direction=direction
    )
```

## Database Query Implementation

**`app/repositories/message_repository.py` (add methods):**
```python
from typing import List, Optional
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.message import MessageResponse

async def get_by_conversation_id(
    self,
    conversation_id: UUID,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    direction: Optional[str] = None
) -> List[MessageResponse]:
    """Get messages for a specific conversation"""

    query = select(self.model_class).options(
        selectinload(self.model_class.conversation)
    ).where(self.model_class.conversation_id == conversation_id)

    # Filter by direction if provided
    if direction:
        query = query.where(self.model_class.direction == direction)

    # Order by message timestamp (oldest first for conversation flow)
    query = query.order_by(self.model_class.message_timestamp.asc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await self.db.execute(query)
    db_models = result.scalars().all()

    return [self._to_pydantic(model) for model in db_models]

def _to_pydantic(self, db_model) -> MessageResponse:
    """Convert MessageModel to MessageResponse"""
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
        updated_at=db_model.updated_at
    )
```

## Test Case (from bin/test.sh)

### Test 8: Get messages for a conversation
```bash
curl -X GET "$BASE_URL/api/conversations/1/messages" \
  -H "$CONTENT_TYPE"
```

## Expected Response
The endpoint should return a JSON array of message objects, each containing:
- `id`: Message UUID
- `conversation_id`: Conversation UUID
- `provider_type`: Type of provider ('sms', 'mms', 'email')
- `provider_message_id`: External provider's message ID
- `from_address`: Sender address
- `to_address`: Recipient address
- `body`: Message content
- `attachments`: Array of attachment URLs
- `direction`: Message direction ('inbound' or 'outbound')
- `status`: Message status ('pending', 'sent', 'delivered', 'failed')
- `message_timestamp`: When the message was sent/received
- `created_at`: When the message was created in our system
- `updated_at`: When the message was last updated

## Implementation Considerations

### Performance
- **Pagination**: Required for conversations with many messages (limit/offset parameters)
- **Eager Loading**: Use `selectinload` to load conversation data efficiently
- **Indexing**: Ensure proper database indexes on conversation_id and message_timestamp

### Filtering
- **By Direction**: Allow filtering by inbound/outbound messages
- **By Date Range**: Could add optional date filtering in the future
- **By Status**: Could add filtering by message status

### Ordering
- **Chronological Order**: Messages ordered by timestamp (oldest first)
- **Alternative Ordering**: Could support newest first if needed

## Error Handling

- Conversation not found (404)
- Invalid conversation ID format
- Invalid limit/offset values
- Invalid direction parameter
- Database connection issues

## Acceptance Criteria

- [ ] GET /api/conversations/{id}/messages returns messages for specific conversation
- [ ] 404 error when conversation doesn't exist
- [ ] Response includes all message metadata (provider info, timestamps, status)
- [ ] Messages ordered chronologically (oldest first)
- [ ] Pagination works correctly (limit/offset parameters)
- [ ] Optional direction filtering works
- [ ] Proper error handling for invalid parameters
- [ ] Database queries are optimized for performance
- [ ] Integration test for entire flow
- [ ] Unit tests for component parts
