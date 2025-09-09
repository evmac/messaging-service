from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import db_session
from app.models.api.conversations import ConversationResponse
from app.models.api.messages import MessageResponse
from app.services.get_conversation_messages_service import (
    GetConversationMessagesService,
)
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
    db: AsyncSession = Depends(db_session),
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
    conversation_id: UUID, db: AsyncSession = Depends(db_session)
) -> ConversationResponse:
    """
    Get detailed information about a specific conversation.

    Path parameters:
    - conversation_id: UUID of the conversation
    """
    try:
        service = ListConversationsService(db)
        conversation = await service.get_conversation_summary(str(conversation_id))
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        # Log the error in production
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: UUID,
    limit: Optional[int] = Query(
        100, description="Maximum number of messages to return", ge=1, le=1000
    ),
    offset: Optional[int] = Query(0, description="Number of messages to skip", ge=0),
    direction: Optional[str] = Query(
        None, description="Filter by message direction ('inbound', 'outbound')"
    ),
    db: AsyncSession = Depends(db_session),
) -> List[MessageResponse]:
    """
    Get all messages for a specific conversation.

    Query parameters:
    - limit: Maximum number of messages to return (default: 100, max: 1000)
    - offset: Number of messages to skip (default: 0)
    - direction: Filter messages by direction ('inbound', 'outbound')
    """
    try:
        service = GetConversationMessagesService(db)
        return await service.get_conversation_messages(
            conversation_id=str(conversation_id),
            limit=limit,
            offset=offset,
            direction=direction,
        )
    except HTTPException:
        # Re-raise HTTP exceptions from the service
        raise
    except Exception:
        # Log the error in production
        raise HTTPException(status_code=500, detail="Internal server error")
