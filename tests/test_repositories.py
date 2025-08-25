from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.api.conversations import ConversationResponse
from app.models.api.messages import MessageResponse
from app.models.api.participants import ParticipantResponse
from app.models.db.conversation_model import ConversationModel
from app.models.db.message_model import MessageModel
from app.models.db.participant_model import ParticipantModel
from app.repositories.base_repository import BaseRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.participant_repository import ParticipantRepository


class TestBaseRepository:
    """Unit tests for BaseRepository functionality."""

    def test_base_repository_creation(self, mock_db: Any) -> None:
        """Test that BaseRepository can be instantiated."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )
        assert repo is not None
        assert repo.db is mock_db
        assert repo.model_class is ConversationModel

    @pytest.mark.asyncio
    async def test_get_by_id_with_mock(self, mock_db: Any) -> None:
        """Test get_by_id method with mocked database."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Mock the database query result
        conversation_id = uuid4()
        mock_db_model = MagicMock(spec=ConversationModel)
        mock_db_model.id = conversation_id
        mock_db_model.created_at = datetime.now(timezone.utc)
        mock_db_model.updated_at = datetime.now(timezone.utc)
        mock_db_model.participants = []
        mock_db_model.messages = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_db_model
        mock_db.execute.return_value = mock_result

        # Mock the _to_pydantic method using patch
        mock_response = ConversationResponse(
            id=conversation_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=[],
            message_count=0,
            last_message_timestamp=None,
        )

        with patch.object(repo, "_to_pydantic", return_value=mock_response):
            # Test the method
            result = await repo.get_by_id(str(conversation_id))

        assert result is not None
        assert result.id == conversation_id
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db: Any) -> None:
        """Test get_by_id when record is not found."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Mock empty result - return None directly, not a coroutine
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Test the method
        result = await repo.get_by_id(str(uuid4()))

        assert result is None

    @pytest.mark.asyncio
    async def test_create(self, mock_db: Any) -> None:
        """Test create method with mocked database."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Create a conversation Pydantic model
        conversation_id = uuid4()
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        conversation_data = ConversationResponse(
            id=conversation_id,
            created_at=created_at,
            updated_at=updated_at,
            participants=[],
            message_count=0,
            last_message_timestamp=None,
        )

        # Mock the database operations
        mock_db_model = MagicMock(spec=ConversationModel)
        mock_db_model.id = conversation_id
        mock_db_model.created_at = created_at
        mock_db_model.updated_at = updated_at

        # Set up database method mocks
        mock_db.add = MagicMock(return_value=None)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)

        # Mock the conversion methods using patch
        with (
            patch.object(repo, "_from_pydantic", return_value=mock_db_model),
            patch.object(repo, "_to_pydantic", return_value=conversation_data),
        ):
            # Test the method
            result = await repo.create(conversation_data)

            assert result is not None
            assert result.id == conversation_id
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, mock_db: Any) -> None:
        """Test delete method with mocked database."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Mock the database query result
        conversation_id = uuid4()
        mock_db_model = MagicMock(spec=ConversationModel)
        mock_db_model.id = conversation_id

        # Set up proper mock chain
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_db_model

        mock_db.execute.return_value = mock_result

        # Test the method
        result = await repo.delete(str(conversation_id))

        assert result is True
        mock_db.delete.assert_called_once_with(mock_db_model)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_db: Any) -> None:
        """Test delete method when record is not found."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Mock empty result - return None directly, not a coroutine
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Test the method
        result = await repo.delete(str(uuid4()))

        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_with_mock(self, mock_db: Any) -> None:
        """Test get_all method with mocked database."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Mock the database query result
        mock_db_models = [
            MagicMock(spec=ConversationModel),
            MagicMock(spec=ConversationModel),
        ]

        # Mock the scalars().all() chain properly
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_db_models)

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result

        # Mock the _to_pydantic method
        mock_responses = [
            ConversationResponse(
                id=uuid4(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                participants=[],
                message_count=0,
                last_message_timestamp=None,
            ),
            ConversationResponse(
                id=uuid4(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                participants=[],
                message_count=0,
                last_message_timestamp=None,
            ),
        ]

        with patch.object(repo, "_to_pydantic", side_effect=mock_responses):
            # Test the method
            result = await repo.get_all(limit=10, offset=0)

        assert len(result) == 2
        assert all(isinstance(item, ConversationResponse) for item in result)
        mock_db.execute.assert_called_once()

    def test_to_pydantic_not_implemented(self, mock_db: Any) -> None:
        """Test that _to_pydantic raises NotImplementedError."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        with pytest.raises(NotImplementedError):
            repo._to_pydantic(None)

    def test_from_pydantic_not_implemented(self, mock_db: Any) -> None:
        """Test that _from_pydantic raises NotImplementedError."""
        repo: BaseRepository[ConversationModel, ConversationResponse] = BaseRepository(
            mock_db, ConversationModel
        )

        # Test with a proper ConversationResponse object
        test_response = ConversationResponse(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            participants=[],
            message_count=0,
            last_message_timestamp=None,
        )

        with pytest.raises(NotImplementedError):
            repo._from_pydantic(test_response)


class TestConversationRepository:
    """Unit tests for ConversationRepository."""

    @pytest.fixture
    def repository(self, mock_db: AsyncMock) -> ConversationRepository:
        """Conversation repository instance."""
        return ConversationRepository(mock_db)

    def test_to_pydantic_conversion(self, repository: ConversationRepository) -> None:
        """Test conversion from SQLAlchemy model to Pydantic model."""
        # Create mock conversation with messages and participants
        conversation_id = uuid4()

        message = MagicMock(spec=MessageModel)
        message.message_timestamp = datetime.now(timezone.utc)

        participant = MagicMock(spec=ParticipantModel)
        participant.address = "test@example.com"

        db_model = MagicMock(spec=ConversationModel)
        db_model.id = conversation_id
        db_model.created_at = datetime.now(timezone.utc)
        db_model.updated_at = datetime.now(timezone.utc)
        db_model.messages = [message]
        db_model.participants = [participant]

        # Convert to Pydantic
        result = repository._to_pydantic(db_model)

        assert isinstance(result, ConversationResponse)
        assert result.id == conversation_id
        assert result.participants == ["test@example.com"]
        assert result.message_count == 1

    def test_from_pydantic_conversion(self, repository: ConversationRepository) -> None:
        """Test conversion from Pydantic model to SQLAlchemy model."""
        conversation_id = uuid4()
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        pydantic_model = ConversationResponse(
            id=conversation_id,
            created_at=created_at,
            updated_at=updated_at,
            participants=["test@example.com"],
            message_count=1,
            last_message_timestamp=None,
        )

        # Convert to SQLAlchemy
        result = repository._from_pydantic(pydantic_model)

        assert isinstance(result, ConversationModel)
        assert result.id == conversation_id
        assert result.created_at == created_at
        assert result.updated_at == updated_at


class TestMessageRepository:
    """Unit tests for MessageRepository."""

    @pytest.fixture
    def repository(self, mock_db: AsyncMock) -> MessageRepository:
        """Message repository instance."""
        return MessageRepository(mock_db)

    def test_to_pydantic_conversion(self, repository: MessageRepository) -> None:
        """Test conversion from SQLAlchemy MessageModel to Pydantic MessageResponse."""
        message_id = uuid4()
        conversation_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        db_model = MagicMock(spec=MessageModel)
        db_model.id = message_id
        db_model.conversation_id = conversation_id
        db_model.provider_type = "email"
        db_model.provider_message_id = "provider_123"
        db_model.from_address = "sender@example.com"
        db_model.to_address = "recipient@example.com"
        db_model.body = "Test message"
        db_model.attachments = ["attachment1.pdf"]
        db_model.direction = "outbound"
        db_model.status = "sent"
        db_model.message_timestamp = timestamp
        db_model.created_at = timestamp
        db_model.updated_at = timestamp

        # Convert to Pydantic
        result = repository._to_pydantic(db_model)

        assert isinstance(result, MessageResponse)
        assert result.id == message_id
        assert result.conversation_id == conversation_id
        assert result.provider_type == "email"
        assert result.body == "Test message"
        assert result.attachments == ["attachment1.pdf"]

    def test_from_pydantic_conversion(self, repository: MessageRepository) -> None:
        """Test conversion from Pydantic MessageResponse to SQLAlchemy
        MessageModel."""
        message_id = uuid4()
        conversation_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        pydantic_model = MessageResponse(
            id=message_id,
            conversation_id=conversation_id,
            provider_type="email",
            provider_message_id="test_123",
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test message body",
            attachments=[],
            direction="outbound",
            status="pending",
            message_timestamp=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )

        # Convert to SQLAlchemy
        result = repository._from_pydantic(pydantic_model)

        assert isinstance(result, MessageModel)
        assert result.id == message_id
        assert result.conversation_id == conversation_id
        assert result.provider_type == "email"


class TestParticipantRepository:
    """Unit tests for ParticipantRepository."""

    @pytest.fixture
    def repository(self, mock_db: AsyncMock) -> ParticipantRepository:
        """Participant repository instance."""
        return ParticipantRepository(mock_db)

    def test_to_pydantic_conversion(self, repository: ParticipantRepository) -> None:
        """Test conversion from SQLAlchemy ParticipantModel to Pydantic
        ParticipantResponse."""
        participant_id = uuid4()
        conversation_id = uuid4()
        created_at = datetime.now(timezone.utc)

        db_model = MagicMock(spec=ParticipantModel)
        db_model.id = participant_id
        db_model.conversation_id = conversation_id
        db_model.address = "+1234567890"
        db_model.address_type = "phone"
        db_model.created_at = created_at

        # Convert to Pydantic
        result = repository._to_pydantic(db_model)

        assert isinstance(result, ParticipantResponse)
        assert result.id == participant_id
        assert result.conversation_id == conversation_id
        assert result.address == "+1234567890"
        assert result.address_type == "phone"

    def test_from_pydantic_conversion(self, repository: ParticipantRepository) -> None:
        """Test conversion from Pydantic ParticipantResponse to SQLAlchemy
        ParticipantModel."""
        participant_id = uuid4()
        conversation_id = uuid4()
        created_at = datetime.now(timezone.utc)

        pydantic_model = ParticipantResponse(
            id=participant_id,
            conversation_id=conversation_id,
            address="user@example.com",
            address_type="email",
            created_at=created_at,
        )

        # Convert to SQLAlchemy
        result = repository._from_pydantic(pydantic_model)

        assert isinstance(result, ParticipantModel)
        assert result.id == participant_id
        assert result.conversation_id == conversation_id
        assert result.address == "user@example.com"
        assert result.address_type == "email"
