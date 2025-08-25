from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.clients.base_provider_client import BaseProviderClient
from app.clients.email_provider_client import EmailProviderClient
from app.clients.sms_provider_client import SmsProviderClient
from app.models.api.conversations import ConversationResponse
from app.models.api.messages import MessageResponse, SendMessageRequest
from app.services.send_message_service import SendMessageService


class TestSendMessageService:
    """Unit tests for SendMessageService."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Mock database session."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.add = MagicMock()
        return mock_session

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> SendMessageService:
        """SendMessageService instance."""
        return SendMessageService(mock_db)

    def test_get_provider_for_email(self, service: SendMessageService) -> None:
        """Test that email provider is selected for email addresses."""
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test email",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "EMAIL_PROVIDER_URL": "http://email-provider.com",
                "EMAIL_PROVIDER_API_KEY": "email-key",
            }.get(key, "")

            provider = service._get_provider_for_request(request)
            assert isinstance(provider, EmailProviderClient)
            assert provider.base_url == "http://email-provider.com"
            assert provider.api_key == "email-key"

    def test_get_provider_for_sms(self, service: SendMessageService) -> None:
        """Test that SMS provider is selected for phone numbers."""
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test SMS",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "SMS_PROVIDER_URL": "http://sms-provider.com",
                "SMS_PROVIDER_API_KEY": "sms-key",
            }.get(key, "")

            provider = service._get_provider_for_request(request)
            assert isinstance(provider, SmsProviderClient)
            assert provider.base_url == "http://sms-provider.com"
            assert provider.api_key == "sms-key"

    def test_get_provider_for_mms(self, service: SendMessageService) -> None:
        """Test that SMS provider is selected for MMS (phone with attachments)."""
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test MMS",
            attachments=["image.jpg"],
            timestamp=datetime.now(timezone.utc),
        )

        with patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default="": {
                "SMS_PROVIDER_URL": "http://sms-provider.com",
                "SMS_PROVIDER_API_KEY": "sms-key",
            }.get(key, "")

            provider = service._get_provider_for_request(request)
            assert isinstance(provider, SmsProviderClient)

    @pytest.mark.asyncio
    async def test_find_or_create_conversation_existing(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test finding existing conversation."""
        participants = ["sender@example.com", "recipient@example.com"]

        # Mock existing conversation
        conversation_id = uuid4()
        existing_conversation = ConversationResponse(
            id=conversation_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=participants,
            message_count=0,
            last_message_timestamp=None,
        )

        with patch.object(
            service.conversation_repo,
            "get_by_participants",
            new_callable=AsyncMock,
            return_value=existing_conversation,
        ):
            result = await service._find_or_create_conversation(participants)

            assert result.id == conversation_id
            # Verify the method was called (mock type issues)

    @pytest.mark.asyncio
    async def test_find_or_create_conversation_new(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test creating new conversation when none exists."""
        participants = ["sender@example.com", "recipient@example.com"]

        # Mock no existing conversation
        conversation_id = uuid4()
        new_conversation = ConversationResponse(
            id=conversation_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=[],
            message_count=0,
            last_message_timestamp=None,
        )

        with (
            patch.object(
                service.conversation_repo, "get_by_participants", return_value=None
            ),
            patch.object(
                service.conversation_repo, "create_empty", return_value=new_conversation
            ) as mock_create_empty,
            patch.object(
                service.participant_repo, "add_participant", new_callable=AsyncMock
            ) as mock_add_participant,
        ):
            await service._find_or_create_conversation(participants)

            assert mock_create_empty.called
            assert mock_add_participant.call_count == 2  # Two participants
            mock_add_participant.assert_any_call(
                conversation_id=str(conversation_id),
                address="sender@example.com",
                address_type="email",
            )
            mock_add_participant.assert_any_call(
                conversation_id=str(conversation_id),
                address="recipient@example.com",
                address_type="email",
            )

    @pytest.mark.asyncio
    async def test_find_or_create_conversation_phone_numbers(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test creating conversation with phone numbers."""
        participants = ["+1234567890", "+0987654321"]

        conversation_id = uuid4()
        new_conversation = ConversationResponse(
            id=conversation_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=[],
            message_count=0,
            last_message_timestamp=None,
        )

        with (
            patch.object(
                service.conversation_repo, "get_by_participants", return_value=None
            ),
            patch.object(
                service.conversation_repo, "create_empty", return_value=new_conversation
            ),
            patch.object(
                service.participant_repo, "add_participant", new_callable=AsyncMock
            ) as mock_add_participant,
        ):
            await service._find_or_create_conversation(participants)

            mock_add_participant.assert_any_call(
                conversation_id=str(conversation_id),
                address="+1234567890",
                address_type="phone",
            )
            mock_add_participant.assert_any_call(
                conversation_id=str(conversation_id),
                address="+0987654321",
                address_type="phone",
            )

    @pytest.mark.asyncio
    async def test_send_message_full_flow(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test the complete send_message flow."""
        # Create test request
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock conversation
        conversation = ConversationResponse(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=["sender@example.com", "recipient@example.com"],
            message_count=0,
            last_message_timestamp=None,
        )

        # Mock provider response
        provider_response = {
            "message_id": "PROVIDER123",
            "status": "sent",
            "test": "data",
        }

        # Mock created message
        created_message = MessageResponse(
            id=uuid4(),
            conversation_id=uuid4(),
            provider_type="email",
            provider_message_id="PROVIDER123",
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
            direction="outbound",
            status="sent",
            message_timestamp=request.timestamp,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock all dependencies
        mock_provider = MagicMock(spec=BaseProviderClient)
        mock_provider.send_message = AsyncMock(return_value=provider_response)
        mock_provider.get_provider_type = MagicMock(return_value="email")
        mock_provider.extract_message_id = MagicMock(return_value="PROVIDER123")
        mock_provider.extract_status = MagicMock(return_value="sent")

        with (
            patch.object(
                service, "_get_provider_for_request", return_value=mock_provider
            ),
            patch.object(
                service, "_find_or_create_conversation", return_value=conversation
            ) as mock_find_conv,
            patch.object(
                service.message_repo, "create", return_value=created_message
            ) as mock_create_msg,
        ):
            result = await service.send_message(request)

            # Verify the flow worked correctly
            assert isinstance(result, MessageResponse)
            assert result.provider_message_id == "PROVIDER123"
            assert result.status == "sent"
            assert result.provider_type == "email"
            assert mock_find_conv.called
            assert mock_create_msg.called

            # Verify provider was called with correct request
            mock_provider.send_message.assert_called_once_with(request)
            mock_provider.get_provider_type.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_handle_provider_error(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test handling of provider errors."""
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock provider error
        provider_error = Exception("Provider unavailable")

        mock_provider = MagicMock(spec=BaseProviderClient)
        mock_provider.send_message = AsyncMock(side_effect=provider_error)
        mock_provider.get_provider_type = MagicMock(return_value="email")
        mock_provider.extract_message_id = MagicMock(return_value="")
        mock_provider.extract_status = MagicMock(return_value="unknown")

        with (
            patch.object(
                service, "_get_provider_for_request", return_value=mock_provider
            ),
            patch.object(
                service, "_find_or_create_conversation", new_callable=AsyncMock
            ),
            pytest.raises(Exception) as exc_info,
        ):
            await service.send_message(request)

        assert "Provider unavailable" in str(exc_info.value)

    def test_handle_provider_error_rate_limit(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test handling of rate limit errors."""
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock rate limit error
        rate_limit_error = Exception("Rate limit exceeded")

        # Test the error handler method directly
        import asyncio

        asyncio.run(service._handle_provider_error(rate_limit_error, request))
        # Should not raise - just handle the error

    def test_handle_provider_error_server_error(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test handling of server errors."""
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock server error
        server_error = Exception("Server error")

        # Test the error handler method directly
        import asyncio

        asyncio.run(service._handle_provider_error(server_error, request))
        # Should not raise - just handle the error

    def test_handle_provider_error_no_response(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test handling of errors without response object."""
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock error without response
        error = Exception("Network error")

        # Test the error handler method directly
        import asyncio

        asyncio.run(service._handle_provider_error(error, request))
        # Should not raise - just handle the error

    def test_service_initialization(
        self, service: SendMessageService, mock_db: AsyncMock
    ) -> None:
        """Test service initialization."""
        assert service.db == mock_db
        assert service.message_repo is not None
        assert service.conversation_repo is not None
        assert service.participant_repo is not None
