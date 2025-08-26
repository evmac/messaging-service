from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.api.messages import MessageResponse
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.get_conversation_messages_service import (
    GetConversationMessagesService,
)


class TestGetConversationMessagesService:
    """Unit tests for GetConversationMessagesService."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Mock database session."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.add = AsyncMock()
        return mock_session

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> GetConversationMessagesService:
        """GetConversationMessagesService instance."""
        return GetConversationMessagesService(mock_db)

    @pytest.fixture
    def sample_conversation_id(self) -> str:
        """Sample conversation ID."""
        return str(uuid4())

    @pytest.fixture
    def sample_messages(self) -> List[MessageResponse]:
        """Sample message responses."""
        now = datetime.now(timezone.utc)
        conversation_id = uuid4()
        return [
            MessageResponse(
                id=uuid4(),
                conversation_id=conversation_id,
                provider_type="sms",
                provider_message_id="msg1",
                from_address="+1234567890",
                to_address="+0987654321",
                body="Hello",
                attachments=[],
                direction="outbound",
                status="delivered",
                message_timestamp=now,
                created_at=now,
                updated_at=now,
            ),
            MessageResponse(
                id=uuid4(),
                conversation_id=conversation_id,
                provider_type="sms",
                provider_message_id="msg2",
                from_address="+0987654321",
                to_address="+1234567890",
                body="Hi there",
                attachments=[],
                direction="inbound",
                status="delivered",
                message_timestamp=now,
                created_at=now,
                updated_at=now,
            ),
        ]

    def test_service_initialization(self, mock_db: AsyncMock) -> None:
        """Test that the service initializes correctly."""
        service = GetConversationMessagesService(mock_db)
        assert service.db == mock_db
        assert isinstance(service.conversation_repo, ConversationRepository)
        assert isinstance(service.message_repo, MessageRepository)

    @pytest.mark.asyncio
    async def test_get_conversation_messages_success(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_conversation_messages with successful retrieval."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ) as mock_get_conversation,
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=sample_messages,
            ) as mock_get_messages,
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id
            )

            # Verify the conversation was checked
            mock_get_conversation.assert_called_once_with(sample_conversation_id)

            # Verify messages were retrieved with correct parameters
            from uuid import UUID

            mock_get_messages.assert_called_once_with(
                conversation_id=UUID(mock_conversation.id),
                limit=100,
                offset=0,
                direction=None,
            )

            # Verify the result
            assert result == sample_messages
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_conversation_messages_with_custom_params(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_conversation_messages with custom parameters."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ) as mock_get_conversation,
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=sample_messages,
            ) as mock_get_messages,
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id,
                limit=50,
                offset=10,
                direction="inbound",
            )

            # Verify the conversation was checked
            mock_get_conversation.assert_called_once_with(sample_conversation_id)

            # Verify messages were retrieved with correct parameters
            from uuid import UUID

            mock_get_messages.assert_called_once_with(
                conversation_id=UUID(mock_conversation.id),
                limit=50,
                offset=10,
                direction="inbound",
            )

            # Verify the result
            assert result == sample_messages

    @pytest.mark.asyncio
    async def test_get_conversation_messages_conversation_not_found(
        self, service: GetConversationMessagesService, sample_conversation_id: str
    ) -> None:
        """Test get_conversation_messages with non-existent conversation."""
        with patch.object(
            service.conversation_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_get_conversation:
            with pytest.raises(HTTPException) as exc_info:
                await service.get_conversation_messages(
                    conversation_id=sample_conversation_id
                )

            assert exc_info.value.status_code == 404
            assert "Conversation not found" in exc_info.value.detail
            mock_get_conversation.assert_called_once_with(sample_conversation_id)

    @pytest.mark.asyncio
    async def test_get_conversation_messages_parameter_validation_valid(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test parameter validation with valid inputs."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=sample_messages,
            ),
        ):
            # Test with valid parameters
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id, limit=1, offset=0
            )
            assert result == sample_messages

            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id, limit=1000, offset=100
            )
            assert result == sample_messages

    @pytest.mark.asyncio
    async def test_get_conversation_messages_parameter_validation_invalid_limit(
        self, service: GetConversationMessagesService, sample_conversation_id: str
    ) -> None:
        """Test parameter validation with invalid limit."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with patch.object(
            service.conversation_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=mock_conversation,
        ):
            # Test invalid limits
            with pytest.raises(HTTPException) as exc_info:
                await service.get_conversation_messages(
                    conversation_id=sample_conversation_id, limit=0
                )
            assert exc_info.value.status_code == 400
            assert "Limit must be between 1 and 1000" in exc_info.value.detail

            with pytest.raises(HTTPException) as exc_info:
                await service.get_conversation_messages(
                    conversation_id=sample_conversation_id, limit=1001
                )
            assert exc_info.value.status_code == 400
            assert "Limit must be between 1 and 1000" in exc_info.value.detail

            with pytest.raises(HTTPException) as exc_info:
                await service.get_conversation_messages(
                    conversation_id=sample_conversation_id, limit=-1
                )
            assert exc_info.value.status_code == 400
            assert "Limit must be between 1 and 1000" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_conversation_messages_parameter_validation_invalid_offset(
        self, service: GetConversationMessagesService, sample_conversation_id: str
    ) -> None:
        """Test parameter validation with invalid offset."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with patch.object(
            service.conversation_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=mock_conversation,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.get_conversation_messages(
                    conversation_id=sample_conversation_id, offset=-1
                )
            assert exc_info.value.status_code == 400
            assert "Offset must be non-negative" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_conversation_messages_parameter_validation_invalid_direction(
        self, service: GetConversationMessagesService, sample_conversation_id: str
    ) -> None:
        """Test parameter validation with invalid direction."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with patch.object(
            service.conversation_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=mock_conversation,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.get_conversation_messages(
                    conversation_id=sample_conversation_id, direction="invalid"
                )
            assert exc_info.value.status_code == 400
            assert (
                "Direction must be 'inbound', 'outbound', or None"
                in exc_info.value.detail
            )

    @pytest.mark.asyncio
    async def test_get_conversation_messages_with_none_params(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_conversation_messages with None parameters (should use defaults)."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=sample_messages,
            ) as mock_get_messages,
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id,
                limit=None,
                offset=None,
                direction=None,
            )

            # Should use default values
            from uuid import UUID

            mock_get_messages.assert_called_once_with(
                conversation_id=UUID(mock_conversation.id),
                limit=100,
                offset=0,
                direction=None,
            )
            assert result == sample_messages

    @pytest.mark.asyncio
    async def test_get_conversation_messages_empty_result(
        self, service: GetConversationMessagesService, sample_conversation_id: str
    ) -> None:
        """Test get_conversation_messages when no messages exist."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id
            )

            assert result == []
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_conversation_messages_single_result(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_conversation_messages with single message."""
        single_message = [sample_messages[0]]

        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=single_message,
            ),
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id
            )

            assert result == single_message
            assert len(result) == 1
            assert result[0].id == sample_messages[0].id

    @pytest.mark.asyncio
    async def test_get_conversation_messages_pagination_edge_cases(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_conversation_messages with edge case pagination values."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=sample_messages,
            ) as mock_get_messages,
        ):
            # Test with zero offset
            await service.get_conversation_messages(
                conversation_id=sample_conversation_id, limit=5, offset=0
            )
            from uuid import UUID

            mock_get_messages.assert_called_with(
                conversation_id=UUID(mock_conversation.id),
                limit=5,
                offset=0,
                direction=None,
            )

            # Test with maximum allowed limit
            await service.get_conversation_messages(
                conversation_id=sample_conversation_id, limit=1000, offset=0
            )
            mock_get_messages.assert_called_with(
                conversation_id=UUID(mock_conversation.id),
                limit=1000,
                offset=0,
                direction=None,
            )

    @pytest.mark.asyncio
    async def test_get_conversation_messages_direction_filtering(
        self,
        service: GetConversationMessagesService,
        sample_conversation_id: str,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_conversation_messages with direction filtering."""
        # Mock the conversation repository to return a conversation
        mock_conversation = AsyncMock()
        mock_conversation.id = sample_conversation_id

        # Filter for inbound messages
        inbound_messages = [sample_messages[1]]  # Second message is inbound
        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=inbound_messages,
            ) as mock_get_messages,
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id, direction="inbound"
            )

            from uuid import UUID

            mock_get_messages.assert_called_once_with(
                conversation_id=UUID(mock_conversation.id),
                limit=100,
                offset=0,
                direction="inbound",
            )
            assert result == inbound_messages
            assert len(result) == 1
            assert result[0].direction == "inbound"

        # Filter for outbound messages
        outbound_messages = [sample_messages[0]]  # First message is outbound
        with (
            patch.object(
                service.conversation_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=mock_conversation,
            ),
            patch.object(
                service.message_repo,
                "get_by_conversation_id",
                new_callable=AsyncMock,
                return_value=outbound_messages,
            ) as mock_get_messages,
        ):
            result = await service.get_conversation_messages(
                conversation_id=sample_conversation_id, direction="outbound"
            )

            mock_get_messages.assert_called_with(
                conversation_id=UUID(mock_conversation.id),
                limit=100,
                offset=0,
                direction="outbound",
            )
            assert result == outbound_messages
            assert len(result) == 1
            assert result[0].direction == "outbound"

    @pytest.mark.asyncio
    async def test_get_message_details_success(
        self,
        service: GetConversationMessagesService,
        sample_messages: List[MessageResponse],
    ) -> None:
        """Test get_message_details with existing message."""
        message = sample_messages[0]
        with patch.object(
            service.message_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=message,
        ) as mock_get_by_id:
            result = await service.get_message_details(str(message.id))

            mock_get_by_id.assert_called_once_with(str(message.id))
            assert result == message

    @pytest.mark.asyncio
    async def test_get_message_details_not_found(
        self, service: GetConversationMessagesService
    ) -> None:
        """Test get_message_details with non-existent message."""
        message_id = str(uuid4())
        with patch.object(
            service.message_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_get_by_id:
            with pytest.raises(HTTPException) as exc_info:
                await service.get_message_details(message_id)

            assert exc_info.value.status_code == 404
            assert "Message not found" in exc_info.value.detail
            mock_get_by_id.assert_called_once_with(message_id)
