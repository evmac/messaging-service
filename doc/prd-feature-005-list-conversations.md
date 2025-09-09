# Feature 5: List Conversations PRD

## Overview
Implement functionality to list all conversations with their metadata.

## Dependencies
- Feature 1: Core Data Layer (Pydantic models, repositories)

## API Endpoint (from test script)
```
GET /api/conversations
```

## Expected Response Format
Based on the test script, the endpoint should return a list of conversations with basic metadata.

## Implementation Requirements

### 1. Service Layer (`app/services/`)

**`app/services/list_conversations_service.py`:**
```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import ConversationResponse
from app.repositories.conversation_repository import ConversationRepository

class ListConversationsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)

    async def list_conversations(
        self,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        participant_address: Optional[str] = None
    ) -> List[ConversationResponse]:
        """
        List conversations with optional filtering:
        1. Retrieve conversations from database
        2. Apply filters if provided
        3. Return formatted responses
        """

        # Step 1: Get conversations from repository
        conversations = await self.conversation_repo.list_conversations(
            limit=limit,
            offset=offset,
            participant_address=participant_address
        )

        # Step 2: Transform to response format
        return conversations

    async def get_conversation_summary(self, conversation_id: str) -> ConversationResponse:
        """Get detailed information about a specific conversation"""
        return await self.conversation_repo.get_by_id(conversation_id)
```

### 2. Router Layer (`app/routers/`)

**`app/routers/conversations.py`:**
```python
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import db_session
from app.models.conversation import ConversationResponse
from app.services.list_conversations_service import ListConversationsService

router = APIRouter()

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    limit: Optional[int] = Query(50, description="Maximum number of conversations to return"),
    offset: Optional[int] = Query(0, description="Number of conversations to skip"),
    participant: Optional[str] = Query(None, description="Filter by participant address"),
    db: AsyncSession = Depends(db_session)
) -> List[ConversationResponse]:
    """
    List all conversations with optional filtering.

    Query parameters:
    - limit: Maximum number of conversations to return (default: 50)
    - offset: Number of conversations to skip (default: 0)
    - participant: Filter conversations by participant address
    """
    service = ListConversationsService(db)
    return await service.list_conversations(
        limit=limit,
        offset=offset,
        participant_address=participant
    )
```

## Database Query Implementation

**`app/repositories/conversation_repository.py` (add methods):**
```python
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.conversation import ConversationResponse

async def list_conversations(
    self,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    participant_address: Optional[str] = None
) -> List[ConversationResponse]:
    """List conversations with optional filtering"""

    query = select(self.model_class).options(
        selectinload(self.model_class.messages),
        selectinload(self.model_class.participants)
    )

    # Filter by participant if provided
    if participant_address:
        query = query.join(self.model_class.participants).where(
            ParticipantModel.address == participant_address
        )

    # Order by last message timestamp (most recent first)
    query = query.order_by(
        # This requires a subquery to get the max timestamp per conversation
        # Implementation depends on the exact schema
    )

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await self.db.execute(query)
    db_models = result.scalars().all()

    return [self._to_pydantic(model) for model in db_models]
```

## Test Case (from bin/test.sh)

### Test 7: Get conversations
```bash
curl -X GET "$BASE_URL/api/conversations" \
  -H "$CONTENT_TYPE"
```

## Expected Response
The endpoint should return a JSON array of conversation objects, each containing:
- `id`: Conversation UUID
- `created_at`: When the conversation was created
- `updated_at`: When the conversation was last updated
- `participants`: Array of participant addresses
- `message_count`: Number of messages in the conversation
- `last_message_timestamp`: Timestamp of the most recent message

## Implementation Considerations

### Performance
- **Pagination**: Required for large datasets (limit/offset parameters)
- **Eager Loading**: Use `selectinload` to avoid N+1 queries when loading participants and messages
- **Indexing**: Ensure proper database indexes on frequently queried fields

### Filtering
- **By Participant**: Allow filtering conversations by a specific participant address
- **By Date Range**: Could add optional date filtering in the future
- **By Message Count**: Could add filtering by conversation activity level

### Ordering
- **By Last Message**: Most recent conversations first (default)
- **By Creation Date**: Oldest conversations first (alternative)
- **By Message Count**: Most active conversations first (alternative)

## Error Handling

- Invalid limit/offset values
- Database connection issues
- Invalid participant address format

## Acceptance Criteria

- [ ] GET /api/conversations returns list of conversations
- [ ] Response includes conversation metadata (participants, message count, timestamps)
- [ ] Pagination works correctly (limit/offset parameters)
- [ ] Optional participant filtering works
- [ ] Conversations ordered by most recent activity
- [ ] Proper error handling for invalid parameters
- [ ] Database queries are optimized (no N+1 problems)
- [ ] Integration test for entire flow
- [ ] Unit tests for component parts
