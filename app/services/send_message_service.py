import os
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.base_provider_client import BaseProviderClient
from app.clients.email_provider_client import EmailProviderClient
from app.clients.sms_provider_client import SmsProviderClient
from app.models.api.conversations import ConversationResponse
from app.models.api.messages import MessageResponse, SendMessageRequest
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.participant_repository import ParticipantRepository


class SendMessageService:
    """Service for sending messages through various providers."""

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
        from datetime import datetime, timezone
        from uuid import uuid4

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
            conversation_id=message.conversation_id,
            provider_type=message.provider_type,
            provider_message_id=message.provider_message_id,
            from_address=message.from_address,
            to_address=message.to_address,
            body=message.body,
            attachments=message.attachments,
            direction=message.direction,
            status=message.status,
            message_timestamp=message.message_timestamp,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    def _get_provider_for_request(
        self, request: SendMessageRequest
    ) -> BaseProviderClient:
        """Determine which provider to use based on recipient address."""
        if "@" in request.to_address:
            return EmailProviderClient(
                base_url=os.getenv("EMAIL_PROVIDER_URL", "http://localhost:8002"),
                api_key=os.getenv("EMAIL_PROVIDER_API_KEY", ""),
            )
        else:
            return SmsProviderClient(
                base_url=os.getenv("SMS_PROVIDER_URL", "http://localhost:8001"),
                api_key=os.getenv("SMS_PROVIDER_API_KEY", ""),
            )

    async def _find_or_create_conversation(
        self, participants: List[str]
    ) -> ConversationResponse:
        """Find existing conversation or create new one with participants."""
        # Check if conversation exists with these participants
        conversation = await self.conversation_repo.get_by_participants(participants)

        if not conversation:
            # Create new conversation
            conversation = await self.conversation_repo.create_empty()

            # Add participants
            for address in participants:
                address_type = "email" if "@" in address else "phone"
                await self.participant_repo.add_participant(
                    conversation_id=str(conversation.id),
                    address=address,
                    address_type=address_type,
                )

        return conversation

    async def _handle_provider_error(
        self, error: Exception, request: SendMessageRequest
    ) -> None:
        """Handle provider errors like rate limits, server errors."""
        if hasattr(error, "response") and error.response:
            if error.response.status_code == 429:
                # Rate limited - could implement retry logic
                pass
            elif error.response.status_code >= 500:
                # Server error - could implement fallback logic
                pass
