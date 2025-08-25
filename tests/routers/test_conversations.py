from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.api.conversations import ConversationResponse


class TestConversationsRouter:
    """Unit tests for the conversations router endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def sample_conversations(self) -> list[ConversationResponse]:
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

    def test_conversations_endpoint_exists(self, client: TestClient) -> None:
        """Test that the conversations endpoint exists."""
        response = client.get("/api/conversations")
        assert response.status_code != 404  # Should not be Not Found

    def test_conversations_endpoint_returns_list(self, client: TestClient) -> None:
        """Test that conversations endpoint returns a list."""
        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/api/conversations")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

    def test_conversations_endpoint_with_pagination(
        self, client: TestClient, sample_conversations: list[ConversationResponse]
    ) -> None:
        """Test conversations endpoint with pagination parameters."""
        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations[:1],
        ):
            response = client.get("/api/conversations?limit=1&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

    def test_conversations_endpoint_with_participant_filter(
        self, client: TestClient, sample_conversations: list[ConversationResponse]
    ) -> None:
        """Test conversations endpoint with participant filter."""
        filtered_conversations = [sample_conversations[0]]  # Email conversation

        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            return_value=filtered_conversations,
        ):
            response = client.get("/api/conversations?participant=user1@example.com")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert "user1@example.com" in data[0]["participants"]

    def test_conversations_endpoint_calls_service(
        self, client: TestClient, sample_conversations: list[ConversationResponse]
    ) -> None:
        """Test that conversations endpoint calls the service layer."""
        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            return_value=sample_conversations,
        ) as mock_service:
            response = client.get(
                "/api/conversations?limit=10&offset=5" "&participant=test@example.com"
            )
            assert response.status_code == 200
            mock_service.assert_called_once()

            # Check that the service was called with correct parameters
            args, kwargs = mock_service.call_args
            assert kwargs["limit"] == 10
            assert kwargs["offset"] == 5
            assert kwargs["participant_address"] == "test@example.com"

    def test_conversations_endpoint_validation_invalid_limit(
        self, client: TestClient
    ) -> None:
        """Test conversations endpoint validation with invalid limit."""
        response = client.get("/api/conversations?limit=0")
        assert (
            response.status_code == 422
        )  # FastAPI uses 422 for query param validation
        assert "greater_than_equal" in str(response.json())

        response = client.get("/api/conversations?limit=1001")
        assert response.status_code == 422
        assert "less_than_equal" in str(response.json())

        response = client.get("/api/conversations?limit=-1")
        assert response.status_code == 422
        assert "greater_than_equal" in str(response.json())

    def test_conversations_endpoint_validation_invalid_offset(
        self, client: TestClient
    ) -> None:
        """Test conversations endpoint validation with invalid offset."""
        response = client.get("/api/conversations?offset=-1")
        assert (
            response.status_code == 422
        )  # FastAPI uses 422 for query param validation
        assert "greater_than_equal" in str(response.json())

    def test_conversations_endpoint_with_malformed_json(
        self, client: TestClient
    ) -> None:
        """Test conversations endpoint with malformed JSON (should not affect GET)."""
        # GET requests don't have request bodies, so this should work fine
        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/api/conversations")
            assert response.status_code == 200

    def test_conversations_endpoint_with_wrong_content_type(
        self, client: TestClient
    ) -> None:
        """Test conversations endpoint with wrong content type."""
        # GET requests don't have request bodies, so content type shouldn't matter
        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get(
                "/api/conversations", headers={"Content-Type": "text/plain"}
            )
            assert response.status_code == 200

    def test_nonexistent_conversations_endpoint(self, client: TestClient) -> None:
        """Test accessing non-existent conversations endpoint."""
        response = client.get("/api/conversations/nonexistent")
        assert response.status_code == 404

    def test_wrong_http_method_conversations(self, client: TestClient) -> None:
        """Test using wrong HTTP method on conversations endpoint."""
        response = client.post("/api/conversations")
        assert response.status_code == 405  # Method Not Allowed

        response = client.put("/api/conversations")
        assert response.status_code == 405

        response = client.delete("/api/conversations")
        assert response.status_code == 405

    def test_get_individual_conversation_success(
        self, client: TestClient, sample_conversations: list[ConversationResponse]
    ) -> None:
        """Test getting individual conversation successfully."""
        conversation = sample_conversations[0]

        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.get_conversation_summary",
            new_callable=AsyncMock,
            return_value=conversation,
        ):
            response = client.get(f"/api/conversations/{conversation.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(conversation.id)
            assert data["participants"] == conversation.participants
            assert data["message_count"] == conversation.message_count

    def test_get_individual_conversation_calls_service(
        self, client: TestClient, sample_conversations: list[ConversationResponse]
    ) -> None:
        """Test that individual conversation endpoint calls the service layer."""
        conversation = sample_conversations[0]

        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.get_conversation_summary",
            new_callable=AsyncMock,
            return_value=conversation,
        ) as mock_service:
            response = client.get(f"/api/conversations/{conversation.id}")
            assert response.status_code == 200
            mock_service.assert_called_once_with(str(conversation.id))

    def test_get_individual_conversation_not_found(self, client: TestClient) -> None:
        """Test getting individual conversation that doesn't exist."""
        conversation_id = str(uuid4())

        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.get_conversation_summary",
            new_callable=AsyncMock,
            side_effect=ValueError(f"Conversation with ID {conversation_id} not found"),
        ):
            response = client.get(f"/api/conversations/{conversation_id}")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_individual_conversation_invalid_uuid(self, client: TestClient) -> None:
        """Test getting individual conversation with invalid UUID."""
        response = client.get("/api/conversations/invalid-uuid")
        assert response.status_code == 404
        assert "badly formed hexadecimal UUID string" in response.json()["detail"]

    def test_get_individual_conversation_wrong_method(self, client: TestClient) -> None:
        """Test using wrong HTTP method on individual conversation endpoint."""
        conversation_id = str(uuid4())

        response = client.post(f"/api/conversations/{conversation_id}")
        assert response.status_code == 405

        response = client.put(f"/api/conversations/{conversation_id}")
        assert response.status_code == 405

        response = client.delete(f"/api/conversations/{conversation_id}")
        assert response.status_code == 405

    def test_conversations_endpoint_service_error_handling(
        self, client: TestClient
    ) -> None:
        """Test conversations endpoint error handling when service raises exception."""
        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.list_conversations",
            new_callable=AsyncMock,
            side_effect=Exception("Service error"),
        ):
            response = client.get("/api/conversations")
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

    def test_individual_conversation_endpoint_service_error_handling(
        self, client: TestClient
    ) -> None:
        """Test individual conversation endpoint error handling."""
        conversation_id = str(uuid4())

        with patch(
            "app.services.list_conversations_service"
            ".ListConversationsService.get_conversation_summary",
            new_callable=AsyncMock,
            side_effect=Exception("Service error"),
        ):
            response = client.get(f"/api/conversations/{conversation_id}")
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
