# Feature 3: SMS/MMS Webhook Processing PRD

## Overview
Implement webhook processing for incoming SMS and MMS messages from the SMS provider.

## Dependencies
- Feature 1: Core Data Layer (Pydantic models, repositories)

## API Endpoint (from test script)
```
POST /api/webhooks/sms
```

## Current SMS Provider Webhook Format

### Inbound SMS (from README.md)
```json
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "sms",
    "messaging_provider_id": "message-1",
    "body": "text message",
    "attachments": null,
    "timestamp": "2024-11-01T14:00:00Z"
}
```

### Inbound MMS (from README.md)
```json
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "mms",
    "messaging_provider_id": "message-2",
    "body": "text message",
    "attachments": ["attachment-url"],
    "timestamp": "2024-11-01T14:00:00Z"
}
```

### SMS Provider Webhook Format (from providers/sms_provider.py)
```python
class IncomingWebhookPayload(BaseModel):
    From: str
    To: str
    Body: str
    MessageSid: str
    MediaUrl: Optional[List[str]] = None
    Timestamp: Optional[str] = None
```

## Implementation Requirements

### 1. Service Layer (`app/services/`)

**`app/services/receive_sms_mms_webhook_service.py`:**
```python
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import WebhookMessageRequest, MessageResponse
from app.repositories.message_repository import MessageRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.participant_repository import ParticipantRepository

class ReceiveSmsMmsWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.message_repo = MessageRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.participant_repo = ParticipantRepository(db)

    async def process_webhook(self, webhook_data: dict) -> MessageResponse:
        """
        Process incoming SMS/MMS webhook:
        1. Validate webhook payload
        2. Transform to internal format
        3. Find or create conversation
        4. Save message to database
        5. Return response
        """

        # Step 1: Validate and normalize webhook data
        request = self._validate_webhook_payload(webhook_data)

        # Step 2: Find or create conversation
        conversation = await self._find_or_create_conversation(
            [request.from_address, request.to_address]
        )

        # Step 3: Save message to database
        message = await self.message_repo.create_inbound_message(
            conversation_id=conversation.id,
            request=request
        )

        # Step 4: Return formatted response
        return MessageResponse(
            id=message.id,
            conversation_id=conversation.id,
            provider_type=request.provider_type,
            provider_message_id=request.provider_message_id,
            from_address=request.from_address,
            to_address=request.to_address,
            body=request.body,
            attachments=request.attachments or [],
            direction="inbound",
            status="delivered",  # Webhook messages are already delivered
            message_timestamp=request.timestamp,
            created_at=message.created_at,
            updated_at=message.updated_at
        )

    def _validate_webhook_payload(self, webhook_data: dict) -> WebhookMessageRequest:
        """Validate and transform webhook payload to internal format"""

        # Handle both provider formats (Twilio-like and our unified format)
        if "From" in webhook_data:
            # SMS Provider format
            from_address = webhook_data["From"]
            to_address = webhook_data["To"]
            body = webhook_data["Body"]
            provider_message_id = webhook_data["MessageSid"]
            attachments = webhook_data.get("MediaUrl", [])
            timestamp_str = webhook_data.get("Timestamp")

            # Determine message type based on attachments
            provider_type = "mms" if attachments else "sms"

        else:
            # Unified format from README
            from_address = webhook_data["from"]
            to_address = webhook_data["to"]
            body = webhook_data["body"]
            provider_message_id = webhook_data["messaging_provider_id"]
            attachments = webhook_data.get("attachments", [])
            timestamp_str = webhook_data["timestamp"]
            provider_type = webhook_data["type"]

        # Parse timestamp
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.utcnow()

        return WebhookMessageRequest(
            from_address=from_address,
            to_address=to_address,
            body=body,
            attachments=attachments,
            provider_message_id=provider_message_id,
            timestamp=timestamp,
            provider_type=provider_type
        )

    async def _find_or_create_conversation(self, participants: List[str]):
        """Find existing conversation or create new one"""
        # Check if conversation exists with these participants
        conversation = await self.conversation_repo.get_by_participants(participants)

        if not conversation:
            # Create new conversation
            conversation = await self.conversation_repo.create_empty()

            # Add participants
            for address in participants:
                address_type = "email" if "@" in address else "phone"
                await self.participant_repo.create(
                    conversation_id=conversation.id,
                    address=address,
                    address_type=address_type
                )

        return conversation
```

### 2. Router Layer (`app/routers/`)

**`app/routers/webhooks.py`:**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import db_session
from app.models.message import MessageResponse
from app.services.receive_sms_mms_webhook_service import ReceiveSmsMmsWebhookService

router = APIRouter()

@router.post("/sms", response_model=MessageResponse)
async def receive_sms_webhook(
    webhook_data: dict,
    db: AsyncSession = Depends(db_session)
) -> MessageResponse:
    """
    Handle incoming SMS/MMS webhooks from SMS provider.
    Supports both Twilio-like format and unified format.
    """
    service = ReceiveSmsMmsWebhookService(db)

    try:
        return await service.process_webhook(webhook_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error and return 500
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Test Cases (from bin/test.sh)

### Test 4: Simulate incoming SMS webhook
```bash
curl -X POST "$BASE_URL/api/webhooks/sms" \
  -H "$CONTENT_TYPE" \
  -d '{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "sms",
    "messaging_provider_id": "message-1",
    "body": "This is an incoming SMS message",
    "attachments": null,
    "timestamp": "2024-11-01T14:00:00Z"
  }'
```

### Test 5: Simulate incoming MMS webhook
```bash
curl -X POST "$BASE_URL/api/webhooks/sms" \
  -H "$CONTENT_TYPE" \
  -d '{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "mms",
    "messaging_provider_id": "message-2",
    "body": "This is an incoming MMS message",
    "attachments": ["https://example.com/received-image.jpg"],
    "timestamp": "2024-11-01T14:00:00Z"
  }'
```

## Message Flow

1. **SMS Provider** sends webhook to `/api/webhooks/sms`
2. **Webhook Router** receives the request and passes it to the service
3. **Service** validates the payload and transforms it to internal format
4. **Service** finds or creates a conversation for the participants
5. **Service** saves the message to the database with direction="inbound"
6. **Service** returns a formatted response

## Error Handling

- Invalid webhook payload format
- Missing required fields
- Database connection issues
- Conversation creation failures

## Acceptance Criteria

- [ ] SMS webhooks processed and saved to database
- [ ] MMS webhooks processed and saved to database
- [ ] Conversations created or found correctly for webhook messages
- [ ] Both SMS provider format and unified format supported
- [ ] Proper error handling for invalid payloads
- [ ] Messages marked with correct direction ("inbound")
- [ ] Webhook responses match expected format
- [ ] Integration test for entire flow
- [ ] Unit tests for component parts
