# Feature 2: Send Message Service PRD

## Overview
Implement the core functionality for sending messages through SMS, MMS, and Email providers.

## Dependencies
- Feature 1: Core Data Layer (Pydantic models, repositories)

## API Endpoints (from test script)
```
POST /api/messages/sms
POST /api/messages/email
```

## Current Provider Implementations

### SMS Provider (`providers/sms_provider.py`)
- Endpoint: `POST /messages`
- Request format:
```python
class MessageRequest(BaseModel):
    From: str
    To: str
    Body: str
    MediaUrl: Optional[List[str]] = None
```
- Response format:
```python
class MessageResponse(BaseModel):
    sid: str
    from_: str
    to: str
    body: str
    status: str
    date_created: str
    date_sent: Optional[str] = None
    media_urls: Optional[List[str]] = None
```

### Email Provider (`providers/email_provider.py`)
- Endpoint: `POST /mail/send`
- Request format: Complex SendGrid-style JSON
- Response format: `{"message_id": str, "status": str}`

## Implementation Requirements

### 1. Provider Abstraction (`app/providers/`)
Create abstract provider interface and concrete implementations:

**`app/clients/base_provider_client.py`:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.message import SendMessageRequest

class BaseProviderClient(ABC):
    @abstractmethod
    async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
        """Send message and return provider response"""
        pass

    @abstractmethod
    def get_provider_type(self) -> str:
        """Return provider type: 'sms', 'mms', or 'email'"""
        pass

class ProviderResponse:
    def __init__(self, provider_message_id: str, status: str, metadata: Dict[str, Any]):
        self.provider_message_id = provider_message_id
        self.status = status
        self.metadata = metadata
```

**`app/providers/sms_provider_client.py`:**
```python
import httpx
from typing import Dict, Any, List
from app.models.message import SendMessageRequest
from app.clients.base_provider_client import BaseProviderClient, ProviderResponse

class SmsProviderClient(BaseProviderClient):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def send_message(self, request: SendMessageRequest) -> ProviderResponse:
        # Transform SendMessageRequest to SMS provider format
        payload = {
            "From": request.from_address,
            "To": request.to_address,
            "Body": request.body,
            "MediaUrl": request.attachments or []
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()

            return ProviderResponse(
                provider_message_id=data["sid"],
                status=data["status"],
                metadata=data
            )

    def get_provider_type(self) -> str:
        # Determine if SMS or MMS based on attachments
        return "mms" if request.attachments else "sms"
```

**`app/providers/email_provider_client.py`:**
```python
import httpx
from typing import Dict, Any, List
from app.models.message import SendMessageRequest
from app.clients.base_provider_client import BaseProviderClient, ProviderResponse

class EmailProviderClient(BaseProviderClient):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def send_message(self, request: SendMessageRequest) -> ProviderResponse:
        # Transform to SendGrid-style payload
        payload = {
            "personalizations": [{
                "to": [{"email": request.to_address}]
            }],
            "from": {"email": request.from_address},
            "subject": "Message",  # Could be extracted from body or made configurable
            "content": [{
                "type": "text/plain",
                "value": request.body
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mail/send",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            response.raise_for_status()
            data = response.json()

            return ProviderResponse(
                provider_message_id=data["message_id"],
                status=data["status"],
                metadata=data
            )

    def get_provider_type(self) -> str:
        return "email"
```

### 2. Service Layer (`app/services/`)

**`app/services/send_message_service.py`:**
```python
from typing import List
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import SendMessageRequest, MessageResponse
from app.repositories.message_repository import MessageRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.participant_repository import ParticipantRepository
from app.clients.base_provider_client import BaseProviderClient, ProviderResponse

class SendMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.message_repo = MessageRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.participant_repo = ParticipantRepository(db)

    async def send_message(self, request: SendMessageRequest) -> MessageResponse:
        """
        Main business logic for sending a message:
        1. Determine provider based on recipient address type
        2. Find or create conversation
        3. Send message via provider
        4. Save message to database
        5. Return response
        """

        # Step 1: Select appropriate provider
        provider = self._get_provider_for_request(request)

        # Step 2: Find or create conversation
        conversation = await self._find_or_create_conversation(
            [request.from_address, request.to_address]
        )

        # Step 3: Send via provider
        try:
            provider_response = await provider.send_message(request)
        except Exception as e:
            # Handle provider errors (429, 500, etc.)
            await self._handle_provider_error(e, request)
            raise

        # Step 4: Create domain model from provider response
        provider_message_id = provider.extract_message_id(provider_response)
        status = provider.extract_status(provider_response)
        provider_type = provider.get_provider_type(request)

        # Create MessageResponse domain model
        message_response = MessageResponse(
            id=uuid4(),
            conversation_id=conversation.id,
            provider_type=provider_type,
            provider_message_id=provider_message_id,
            from_address=request.from_address,
            to_address=request.to_address,
            body=request.body,
            attachments=request.attachments or [],
            direction="outbound",
            status=status,
            message_timestamp=request.timestamp,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Step 5: Save to database
        message = await self.message_repo.create(message_response)

        # Step 6: Return formatted response
        return MessageResponse(
            id=message.id,
            conversation_id=conversation.id,
            provider_type=provider.get_provider_type(),
            provider_message_id=provider_message_id,
            from_address=request.from_address,
            to_address=request.to_address,
            body=request.body,
            attachments=request.attachments or [],
            direction="outbound",
            status=status,
            message_timestamp=request.timestamp,
            created_at=message.created_at,
            updated_at=message.updated_at
        )

    def _get_provider_for_request(self, request: SendMessageRequest) -> BaseProvider:
        """Determine which provider to use based on recipient address"""
        if "@" in request.to_address:
            return EmailProviderClient(
                base_url=os.getenv("EMAIL_PROVIDER_URL"),
                api_key=os.getenv("EMAIL_PROVIDER_API_KEY")
            )
        else:
            return SmsProviderClient(
                base_url=os.getenv("SMS_PROVIDER_URL"),
                api_key=os.getenv("SMS_PROVIDER_API_KEY")
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

    async def _handle_provider_error(self, error: Exception, request: SendMessageRequest):
        """Handle provider errors like rate limits, server errors"""
        if hasattr(error, 'response') and error.response:
            if error.response.status_code == 429:
                # Rate limited - could implement retry logic
                pass
            elif error.response.status_code >= 500:
                # Server error - could implement fallback logic
                pass
```

### 3. Router Layer (`app/routers/`)

**`app/routers/messages.py`:**
```python
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import db_session
from app.models.message import SendMessageRequest, MessageResponse
from app.services.send_message_service import SendMessageService

router = APIRouter()

@router.post("/sms", response_model=MessageResponse)
async def send_sms(
    request: SendMessageRequest,
    db: AsyncSession = Depends(db_session)
) -> MessageResponse:
    """Send SMS or MMS message"""
    service = SendMessageService(db)
    return await service.send_message(request)

@router.post("/email", response_model=MessageResponse)
async def send_email(
    request: SendMessageRequest,
    db: AsyncSession = Depends(db_session)
) -> MessageResponse:
    """Send email message"""
    service = SendMessageService(db)
    return await service.send_message(request)
```

## Test Cases (from bin/test.sh)
- Send SMS: Basic text message
- Send MMS: Message with attachments
- Send Email: HTML formatted message with attachments

## Error Handling
- Provider rate limiting (429)
- Provider server errors (500)
- Invalid message format
- Database connection issues

## Acceptance Criteria
- [ ] SMS messages sent successfully via SMS provider
- [ ] MMS messages sent successfully via SMS provider
- [ ] Email messages sent successfully via Email provider
- [ ] Messages saved to database with correct status
- [ ] Conversations created or found correctly
- [ ] Provider errors handled appropriately
- [ ] API responses match expected format
- [ ] Integration test for entire flow
- [ ] Unit tests for component parts
