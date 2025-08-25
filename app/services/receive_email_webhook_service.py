from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.conversations import ConversationResponse
from app.models.api.messages import MessageResponse, WebhookMessageRequest
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.participant_repository import ParticipantRepository


class ReceiveEmailWebhookService:
    """Service for processing incoming email webhooks."""

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

        # Handle both provider formats (SendGrid-like and our unified format)
        from_address: str
        to_address: str
        body: str
        provider_message_id: str
        attachments: List[str]
        timestamp_str: Optional[str]

        if "from_email" in webhook_data:
            # Email Provider format (SendGrid-like)
            from_address = str(webhook_data.get("from_email", ""))
            to_address = str(webhook_data.get("to_email", ""))
            subject = str(webhook_data.get("subject", ""))
            content = str(webhook_data.get("content", ""))
            html_content = webhook_data.get("html_content")
            provider_message_id = str(webhook_data.get("x_message_id", ""))
            attachments = []  # Email provider doesn't specify attachments in webhook
            timestamp_str = webhook_data.get("timestamp")

            # Use HTML content if available, otherwise plain text
            body = html_content if html_content else content

            # Prepend subject to body if present (for conversation context)
            if subject:
                body = f"Subject: {subject}\n\n{body}"

        elif "from" in webhook_data:
            # Unified format from README
            from_address = str(webhook_data.get("from", ""))
            to_address = str(webhook_data.get("to", ""))
            body = str(webhook_data.get("body", ""))
            provider_message_id = str(webhook_data.get("xillio_id", ""))
            attachments = webhook_data.get("attachments", []) or []
            timestamp_str = webhook_data.get("timestamp")

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

        # Validate email addresses contain @ symbol
        if "@" not in from_address:
            raise ValueError(f"Invalid from_address format: {from_address}")
        if "@" not in to_address:
            raise ValueError(f"Invalid to_address format: {to_address}")

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
            provider_type="email",
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
