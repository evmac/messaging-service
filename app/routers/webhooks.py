from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api.messages import MessageResponse
from app.services.receive_sms_mms_webhook_service import ReceiveSmsMmsWebhookService

router = APIRouter()


@router.post("/sms", response_model=MessageResponse)
async def receive_sms_webhook(
    webhook_data: dict, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Handle incoming SMS/MMS webhooks from SMS provider.
    Supports both Twilio-like format and unified format.
    """
    service = ReceiveSmsMmsWebhookService(db)

    try:
        return await service.process_webhook(webhook_data)
    except ValueError as e:
        # Validation errors (invalid payload format, missing fields)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error and return 500 for unexpected errors
        # In production, you might want to use a proper logger here
        print(f"Unexpected error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
