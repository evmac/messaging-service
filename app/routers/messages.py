from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api.messages import MessageResponse, SendMessageRequest
from app.services.send_message_service import SendMessageService

router = APIRouter()


@router.post("/sms", response_model=MessageResponse)
async def send_sms(
    request: SendMessageRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Send SMS or MMS message."""
    service = SendMessageService(db)
    return await service.send_message(request)


@router.post("/email", response_model=MessageResponse)
async def send_email(
    request: SendMessageRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Send email message."""
    service = SendMessageService(db)
    return await service.send_message(request)
