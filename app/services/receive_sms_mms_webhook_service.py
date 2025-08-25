from datetime import datetime, timezone
from typing import Any, List, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.conversations import ConversationResponse
from app.models.api.messages import MessageResponse, WebhookMessageRequest
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.participant_repository import ParticipantRepository


class ReceiveSmsMmsWebhookService:
    """Service for processing incoming SMS/MMS webhooks."""

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
            conversation_id=conversation.id, request=request
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
            updated_at=message.updated_at,
        )

    def _validate_webhook_payload(self, webhook_data: Any) -> WebhookMessageRequest:
        """Validate and transform webhook payload to internal format"""
        if not isinstance(webhook_data, dict):
            raise ValueError("Webhook payload must be a dictionary")

        # Handle both provider formats (Twilio-like and our unified format)
        from_address: str
        to_address: str
        body: str
        provider_message_id: str
        provider_type: str
        attachments: List[str]
        timestamp_str: Union[str, None]

        if "from" in webhook_data:
            # Unified format from README
            from_address = str(webhook_data.get("from", ""))
            to_address = str(webhook_data.get("to", ""))
            body = str(webhook_data.get("body", ""))
            provider_message_id = str(webhook_data.get("messaging_provider_id", ""))
            attachments = webhook_data.get("attachments", []) or []
            timestamp_str = webhook_data.get("timestamp")
            provider_type = str(webhook_data.get("type", ""))

        elif "From" in webhook_data:
            # SMS Provider format (Twilio-like)
            from_address = str(webhook_data.get("From", ""))
            to_address = str(webhook_data.get("To", ""))
            body = str(webhook_data.get("Body", ""))
            provider_message_id = str(webhook_data.get("MessageSid", ""))
            attachments = webhook_data.get("MediaUrl", []) or []
            timestamp_str = webhook_data.get("Timestamp")

            # Determine message type based on attachments
            provider_type = "mms" if attachments else "sms"

        else:
            raise ValueError("Invalid webhook format: missing required fields")

        # Validate required fields with proper type checking
        if not from_address or not isinstance(from_address, str):
            raise ValueError("Missing required field: from_address")
        if not to_address or not isinstance(to_address, str):
            raise ValueError("Missing required field: to_address")
        if not body or not isinstance(body, str):
            raise ValueError("Missing required field: body")
        if not provider_message_id or not isinstance(provider_message_id, str):
            raise ValueError("Missing required field: provider_message_id")
        if not provider_type or not isinstance(provider_type, str):
            raise ValueError("Missing required field: provider_type")

        # Validate provider type
        if provider_type not in ["sms", "mms"]:
            raise ValueError(
                f"Invalid provider_type: {provider_type}. Must be 'sms' or 'mms'"
            )

        # Parse timestamp
        if timestamp_str:
            try:
                # Handle ISO format with 'Z' suffix
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e
        else:
            timestamp = datetime.now(timezone.utc)

        return WebhookMessageRequest(
            from_address=from_address,
            to_address=to_address,
            body=body,
            attachments=attachments,
            provider_message_id=provider_message_id,
            timestamp=timestamp,
            provider_type=provider_type,
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
