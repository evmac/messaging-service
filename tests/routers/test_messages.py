from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.api.messages import MessageResponse, SendMessageRequest


class TestMessagesRouter:
    """Unit tests for the messages router endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def sample_message_request(self) -> dict:
        """Sample message request data."""
        return {
            "from_address": "+1234567890",
            "to_address": "+0987654321",
            "body": "Test message",
            "attachments": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.fixture
    def sample_message_response(self) -> MessageResponse:
        """Sample message response."""
        return MessageResponse(
            id=uuid4(),
            conversation_id=uuid4(),
            provider_type="sms",
            provider_message_id="SM1234567890",
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test message",
            attachments=[],
            direction="outbound",
            status="sent",
            message_timestamp=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_sms_endpoint_exists(self, client: TestClient) -> None:
        """Test that SMS endpoint exists and is accessible."""
        # Test OPTIONS request (CORS preflight)
        response = client.options("/api/messages/sms")
        assert response.status_code in [200, 404, 405]  # 405 if OPTIONS not allowed

        # Test POST request with invalid data to check endpoint exists
        response = client.post("/api/messages/sms", json={})
        assert response.status_code == 422  # Validation error, but endpoint exists

    def test_email_endpoint_exists(self, client: TestClient) -> None:
        """Test that email endpoint exists and is accessible."""
        # Test OPTIONS request (CORS preflight)
        response = client.options("/api/messages/email")
        assert response.status_code in [200, 404, 405]  # 405 if OPTIONS not allowed

        # Test POST request with invalid data to check endpoint exists
        response = client.post("/api/messages/email", json={})
        assert response.status_code == 422  # Validation error, but endpoint exists

    @pytest.mark.asyncio
    async def test_sms_endpoint_calls_service(
        self,
        client: TestClient,
        sample_message_request: dict,
        sample_message_response: MessageResponse,
    ) -> None:
        """Test that SMS endpoint properly calls the service."""
        with patch("app.routers.messages.SendMessageService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.send_message = AsyncMock(return_value=sample_message_response)
            mock_service_class.return_value = mock_service

            response = client.post("/api/messages/sms", json=sample_message_request)

            assert response.status_code == 200
            assert mock_service_class.called
            assert mock_service.send_message.called

            # Verify the service was called with the correct request data
            call_args = mock_service.send_message.call_args[0][0]
            assert isinstance(call_args, SendMessageRequest)
            assert call_args.from_address == sample_message_request["from_address"]
            assert call_args.to_address == sample_message_request["to_address"]
            assert call_args.body == sample_message_request["body"]

    @pytest.mark.asyncio
    async def test_email_endpoint_calls_service(
        self, client: TestClient, sample_message_response: MessageResponse
    ) -> None:
        """Test that email endpoint properly calls the service."""
        email_request = {
            "from_address": "sender@example.com",
            "to_address": "recipient@example.com",
            "body": "Test email",
            "attachments": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with patch("app.routers.messages.SendMessageService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.send_message = AsyncMock(return_value=sample_message_response)
            mock_service_class.return_value = mock_service

            response = client.post("/api/messages/email", json=email_request)

            assert response.status_code == 200
            assert mock_service_class.called
            assert mock_service.send_message.called

            # Verify the service was called with the correct request data
            call_args = mock_service.send_message.call_args[0][0]
            assert isinstance(call_args, SendMessageRequest)
            assert call_args.from_address == email_request["from_address"]
            assert call_args.to_address == email_request["to_address"]

    def test_sms_endpoint_validation(self, client: TestClient) -> None:
        """Test SMS endpoint input validation."""
        # Missing required fields
        invalid_data = {
            "to_address": "+0987654321",
            "body": "Test message",
            # Missing from_address
        }

        response = client.post("/api/messages/sms", json=invalid_data)
        assert response.status_code == 422

        response_data = response.json()
        assert "detail" in response_data

    def test_email_endpoint_validation(self, client: TestClient) -> None:
        """Test email endpoint input validation."""
        # Missing required fields
        invalid_data = {
            "from_address": "sender@example.com",
            "body": "Test email",
            # Missing to_address
        }

        response = client.post("/api/messages/email", json=invalid_data)
        assert response.status_code == 422

        response_data = response.json()
        assert "detail" in response_data

    def test_endpoint_with_malformed_json(self, client: TestClient) -> None:
        """Test endpoints with malformed JSON."""
        response = client.post(
            "/api/messages/sms",
            content=b"invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_endpoint_with_wrong_content_type(self, client: TestClient) -> None:
        """Test endpoints with wrong content type."""
        response = client.post(
            "/api/messages/sms",
            content=b"not json",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422

    def test_nonexistent_endpoint(self, client: TestClient) -> None:
        """Test that non-existent endpoints return 404."""
        response = client.post("/api/messages/nonexistent", json={})
        assert response.status_code == 404

    def test_wrong_http_method(self, client: TestClient) -> None:
        """Test that wrong HTTP methods return appropriate errors."""
        # GET request to POST endpoint
        response = client.get("/api/messages/sms")
        assert response.status_code == 405  # Method Not Allowed

        response = client.get("/api/messages/email")
        assert response.status_code == 405  # Method Not Allowed
