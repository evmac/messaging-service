from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api.conversations import ConversationResponse
from app.services.list_conversations_service import ListConversationsService

router = APIRouter()


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    limit: Optional[int] = Query(
        50, description="Maximum number of conversations to return", ge=1, le=1000
    ),
    offset: Optional[int] = Query(
        0, description="Number of conversations to skip", ge=0
    ),
    participant: Optional[str] = Query(
        None, description="Filter by participant address"
    ),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """
    List all conversations with optional filtering.

    Query parameters:
    - limit: Maximum number of conversations to return (default: 50, max: 1000)
    - offset: Number of conversations to skip (default: 0)
    - participant: Filter conversations by participant address
    """
    try:
        service = ListConversationsService(db)
        return await service.list_conversations(
            limit=limit, offset=offset, participant_address=participant
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Log the error in production
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str, db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Get detailed information about a specific conversation.

    Path parameters:
    - conversation_id: UUID of the conversation
    """
    try:
        service = ListConversationsService(db)
        conversation = await service.get_conversation_summary(conversation_id)
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        # Log the error in production
        raise HTTPException(status_code=500, detail="Internal server error")
