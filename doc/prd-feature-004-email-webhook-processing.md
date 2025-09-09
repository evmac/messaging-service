# Feature 4: Email Webhook Processing PRD

## Overview
Implement webhook processing for incoming email messages from the Email provider.

## Dependencies
- Feature 1: Core Data Layer (Pydantic models, repositories)

## API Endpoint (from test script)
```
POST /api/webhooks/email
```

## Current Email Provider Webhook Format

### Inbound Email (from README.md)
```json
{
    "from": "contact@gmail.com",
    "to": "user@usehatchapp.com",
    "xillio_id": "message-3",
    "body": "<html><body>This is an incoming email with <b>HTML</b> content</body></html>",
    "attachments": ["https://example.com/received-document.pdf"],
    "timestamp": "2024-11-01T14:00:00Z"
}
```

### Email Provider Webhook Format (from providers/email_provider.py)
```python
class IncomingEmailWebhook(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    subject: str
    content: str
    html_content: Optional[str] = None
    x_message_id: str
    timestamp: Optional[str] = None
```

## Implementation Requirements

### 1. Service Layer (`app/services/`)

**`app/services/receive_email_webhook_service.py`:**
```python
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import WebhookMessageRequest, MessageResponse
from app.repositories.message_repository import MessageRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.participant_repository import ParticipantRepository

class ReceiveEmailWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.message_repo = MessageRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.participant_repo = ParticipantRepository(db)

    async def process_webhook(self, webhook_data: dict) -> MessageResponse:
        """
        Process incoming email webhook:
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

        # Handle both provider formats (SendGrid-like and our unified format)
        if "from_email" in webhook_data:
            # Email Provider format
            from_address = webhook_data["from_email"]
            to_address = webhook_data["to_email"]
            body = webhook_data.get("html_content") or webhook_data["content"]
            provider_message_id = webhook_data["x_message_id"]
            attachments = []  # Email provider doesn't specify attachments in webhook
            timestamp_str = webhook_data.get("timestamp")

        else:
            # Unified format from README
            from_address = webhook_data["from"]
            to_address = webhook_data["to"]
            body = webhook_data["body"]
            provider_message_id = webhook_data["xillio_id"]
            attachments = webhook_data.get("attachments", [])
            timestamp_str = webhook_data["timestamp"]

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
            provider_type="email"
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

**`app/routers/webhooks.py` (add to existing file):**
```python
from app.services.receive_email_webhook_service import ReceiveEmailWebhookService

@router.post("/email", response_model=MessageResponse)
async def receive_email_webhook(
    webhook_data: dict,
    db: AsyncSession = Depends(db_session)
) -> MessageResponse:
    """
    Handle incoming email webhooks from Email provider.
    Supports both SendGrid-like format and unified format.
    """
    service = ReceiveEmailWebhookService(db)

    try:
        return await service.process_webhook(webhook_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error and return 500
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Test Case (from bin/test.sh)

### Test 6: Simulate incoming Email webhook
```bash
curl -X POST "$BASE_URL/api/webhooks/email" \
  -H "$CONTENT_TYPE" \
  -d '{
    "from": "contact@gmail.com",
    "to": "user@usehatchapp.com",
    "xillio_id": "message-3",
    "body": "<html><body>This is an incoming email with <b>HTML</b> content</body></html>",
    "attachments": ["https://example.com/received-document.pdf"],
    "timestamp": "2024-11-01T14:00:00Z"
  }'
```

## Message Flow

1. **Email Provider** sends webhook to `/api/webhooks/email`
2. **Webhook Router** receives the request and passes it to the service
3. **Service** validates the payload and transforms it to internal format
4. **Service** finds or creates a conversation for the participants
5. **Service** saves the message to the database with direction="inbound"
6. **Service** returns a formatted response

## Email-Specific Considerations

- **HTML Content**: Email providers may send both HTML and plain text versions
- **Subject Lines**: Unlike SMS, emails have subject lines (could be stored in message body or separate field)
- **Reply Handling**: Email conversations may have reply threads
- **Attachments**: Email attachments are handled differently than MMS attachments

## Error Handling

- Invalid webhook payload format
- Missing required fields (from, to, xillio_id)
- Malformed email addresses
- Database connection issues
- HTML parsing errors

## Acceptance Criteria

- [ ] Email webhooks processed and saved to database
- [ ] Both email provider format and unified format supported
- [ ] HTML content properly handled and stored
- [ ] Conversations created or found correctly for email messages
- [ ] Proper error handling for invalid email payloads
- [ ] Messages marked with correct direction ("inbound") and provider_type ("email")
- [ ] Webhook responses match expected format
- [ ] Integration test for entire flow
- [ ] Unit tests for component parts
