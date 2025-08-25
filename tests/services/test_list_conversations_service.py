from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.api.conversations import ConversationResponse
from app.repositories.conversation_repository import ConversationRepository
from app.services.list_conversations_service import ListConversationsService


class TestListConversationsService:
    """Unit tests for ListConversationsService."""

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
    def mock_conversation_repo(self, mock_db: AsyncMock) -> ConversationRepository:
        """Mock conversation repository."""
        return ConversationRepository(mock_db)

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ListConversationsService:
        """ListConversationsService instance."""
        return ListConversationsService(mock_db)

    @pytest.fixture
    def sample_conversations(self) -> List[ConversationResponse]:
        """Sample conversation responses."""
        now = datetime.now(timezone.utc)
        return [
            ConversationResponse(
                id=uuid4(),
                created_at=now,
                updated_at=now,
                participants=["user1@example.com", "user2@example.com"],
                message_count=6,
                last_message_timestamp=now,
            ),
            ConversationResponse(
                id=uuid4(),
                created_at=now,
                updated_at=now,
                participants=["+1234567890", "+0987654321"],
                message_count=3,
                last_message_timestamp=now,
            ),
        ]

    def test_service_initialization(self, mock_db: AsyncMock) -> None:
        """Test that the service initializes correctly."""
        service = ListConversationsService(mock_db)
        assert service.db == mock_db
        assert isinstance(service.conversation_repo, ConversationRepository)

    @pytest.mark.asyncio
    async def test_list_conversations_default_params(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test list_conversations with default parameters."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations,
        ) as mock_list_conversations:
            result = await service.list_conversations()

            # Verify the repository was called with correct parameters
            mock_list_conversations.assert_called_once_with(
                limit=50, offset=0, participant_address=None
            )

            # Verify the result
            assert result == sample_conversations
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_conversations_with_custom_params(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test list_conversations with custom parameters."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations,
        ) as mock_list_conversations:
            result = await service.list_conversations(
                limit=10, offset=20, participant_address="user@example.com"
            )

            # Verify the repository was called with correct parameters
            mock_list_conversations.assert_called_once_with(
                limit=10, offset=20, participant_address="user@example.com"
            )

            # Verify the result
            assert result == sample_conversations

    @pytest.mark.asyncio
    async def test_list_conversations_parameter_validation_valid(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test parameter validation with valid inputs."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations,
        ):
            # Test with valid parameters
            result = await service.list_conversations(limit=1, offset=0)
            assert result == sample_conversations

            result = await service.list_conversations(limit=1000, offset=100)
            assert result == sample_conversations

    @pytest.mark.asyncio
    async def test_list_conversations_parameter_validation_invalid_limit(
        self, service: ListConversationsService
    ) -> None:
        """Test parameter validation with invalid limit."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
                await service.list_conversations(limit=0)

            with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
                await service.list_conversations(limit=1001)

            with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
                await service.list_conversations(limit=-1)

    @pytest.mark.asyncio
    async def test_list_conversations_parameter_validation_invalid_offset(
        self, service: ListConversationsService
    ) -> None:
        """Test parameter validation with invalid offset."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with pytest.raises(ValueError, match="Offset must be non-negative"):
                await service.list_conversations(offset=-1)

    @pytest.mark.asyncio
    async def test_list_conversations_with_none_params(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test list_conversations with None parameters (should use defaults)."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations,
        ) as mock_list_conversations:
            result = await service.list_conversations(
                limit=None, offset=None, participant_address=None
            )

            # Should use default values
            mock_list_conversations.assert_called_once_with(
                limit=50, offset=0, participant_address=None
            )
            assert result == sample_conversations

    @pytest.mark.asyncio
    async def test_get_conversation_summary_success(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test get_conversation_summary with existing conversation."""
        conversation = sample_conversations[0]
        with patch.object(
            service.conversation_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=conversation,
        ) as mock_get_by_id:
            result = await service.get_conversation_summary(str(conversation.id))

            mock_get_by_id.assert_called_once_with(str(conversation.id))
            assert result == conversation

    @pytest.mark.asyncio
    async def test_get_conversation_summary_not_found(
        self, service: ListConversationsService
    ) -> None:
        """Test get_conversation_summary with non-existent conversation."""
        conversation_id = str(uuid4())
        with patch.object(
            service.conversation_repo,
            "get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_get_by_id:
            with pytest.raises(
                ValueError, match=f"Conversation with ID {conversation_id} not found"
            ):
                await service.get_conversation_summary(conversation_id)

            mock_get_by_id.assert_called_once_with(conversation_id)

    @pytest.mark.asyncio
    async def test_list_conversations_empty_result(
        self, service: ListConversationsService
    ) -> None:
        """Test list_conversations when no conversations exist."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.list_conversations()

            assert result == []
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_conversations_single_result(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test list_conversations with single conversation."""
        single_conversation = [sample_conversations[0]]
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=single_conversation,
        ):
            result = await service.list_conversations()

            assert result == single_conversation
            assert len(result) == 1
            assert result[0].id == sample_conversations[0].id

    @pytest.mark.asyncio
    async def test_list_conversations_pagination_edge_cases(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test list_conversations with edge case pagination values."""
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations,
        ) as mock_list_conversations:
            # Test with zero offset
            await service.list_conversations(limit=5, offset=0)
            mock_list_conversations.assert_called_with(
                limit=5, offset=0, participant_address=None
            )

            # Test with maximum allowed limit
            await service.list_conversations(limit=1000, offset=0)
            mock_list_conversations.assert_called_with(
                limit=1000, offset=0, participant_address=None
            )

    @pytest.mark.asyncio
    async def test_list_conversations_participant_filtering(
        self,
        service: ListConversationsService,
        sample_conversations: List[ConversationResponse],
    ) -> None:
        """Test list_conversations with participant filtering."""
        # Filter for email conversations
        email_conversations = [
            sample_conversations[0]
        ]  # First conversation has email addresses
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=email_conversations,
        ) as mock_list_conversations:
            result = await service.list_conversations(
                participant_address="user1@example.com"
            )

            mock_list_conversations.assert_called_once_with(
                limit=50, offset=0, participant_address="user1@example.com"
            )
            assert result == email_conversations

        # Filter for phone conversations
        phone_conversations = [
            sample_conversations[1]
        ]  # Second conversation has phone numbers
        with patch.object(
            service.conversation_repo,
            "list_conversations",
            new_callable=AsyncMock,
            return_value=phone_conversations,
        ) as mock_list_conversations:
            result = await service.list_conversations(participant_address="+1234567890")

            mock_list_conversations.assert_called_with(
                limit=50, offset=0, participant_address="+1234567890"
            )
            assert result == phone_conversations
