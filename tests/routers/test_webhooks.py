from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.api.messages import MessageResponse


class TestWebhooksRouter:
    """Integration tests for the webhooks router endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def sample_sms_webhook_data(self) -> dict:
        """Sample SMS webhook data in unified format."""
        return {
            "from": "+18045551234",
            "to": "+12016661234",
            "type": "sms",
            "messaging_provider_id": "message-1",
            "body": "This is an incoming SMS message",
            "attachments": [],
            "timestamp": "2024-11-01T14:00:00Z",
        }

    @pytest.fixture
    def sample_mms_webhook_data(self) -> dict:
        """Sample MMS webhook data in unified format."""
        return {
            "from": "+18045551234",
            "to": "+12016661234",
            "type": "mms",
            "messaging_provider_id": "message-2",
            "body": "This is an incoming MMS message",
            "attachments": ["https://example.com/received-image.jpg"],
            "timestamp": "2024-11-01T14:00:00Z",
        }

    @pytest.fixture
    def sample_sms_provider_webhook_data(self) -> dict:
        """Sample SMS webhook data in SMS provider format (Twilio-like)."""
        return {
            "From": "+18045551234",
            "To": "+12016661234",
            "Body": "Test SMS from provider",
            "MessageSid": "SM1234567890",
            "MediaUrl": [],
            "Timestamp": "2024-11-01T14:00:00Z",
        }

    @pytest.fixture
    def sample_mms_provider_webhook_data(self) -> dict:
        """Sample MMS webhook data in SMS provider format."""
        return {
            "From": "+18045551234",
            "To": "+12016661234",
            "Body": "Test MMS from provider",
            "MessageSid": "MM1234567890",
            "MediaUrl": ["https://api.twilio.com/Messages/MM123/Media/ME123"],
            "Timestamp": "2024-11-01T14:00:00Z",
        }

    @pytest.fixture
    def sample_message_response(self) -> MessageResponse:
        """Sample message response."""
        return MessageResponse(
            id=uuid4(),
            conversation_id=uuid4(),
            provider_type="sms",
            provider_message_id="message-1",
            from_address="+18045551234",
            to_address="+12016661234",
            body="This is an incoming SMS message",
            attachments=[],
            direction="inbound",
            status="delivered",
            message_timestamp=datetime.fromisoformat("2024-11-01T14:00:00+00:00"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_webhook_endpoint_exists(self, client: TestClient) -> None:
        """Test that SMS webhook endpoint exists and is accessible."""
        # Test OPTIONS request (CORS preflight)
        response = client.options("/api/webhooks/sms")
        assert response.status_code in [200, 404, 405]  # 405 if OPTIONS not allowed

        # Test POST request with invalid data to check endpoint exists
        response = client.post("/api/webhooks/sms", json={})
        assert response.status_code == 400  # Validation error, but endpoint exists

    @pytest.mark.asyncio
    async def test_sms_webhook_unified_format(
        self,
        client: TestClient,
        sample_sms_webhook_data: dict,
        sample_message_response: MessageResponse,
    ) -> None:
        """Test SMS webhook processing with unified format."""
        with patch(
            "app.routers.webhooks.ReceiveSmsMmsWebhookService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_webhook = AsyncMock(
                return_value=sample_message_response
            )
            mock_service_class.return_value = mock_service

            response = client.post("/api/webhooks/sms", json=sample_sms_webhook_data)

            assert response.status_code == 200
            assert mock_service_class.called
            assert mock_service.process_webhook.called

            # Verify the service was called with the correct webhook data
            call_args = mock_service.process_webhook.call_args[0][0]
            assert call_args == sample_sms_webhook_data

    @pytest.mark.asyncio
    async def test_mms_webhook_unified_format(
        self,
        client: TestClient,
        sample_mms_webhook_data: dict,
        sample_message_response: MessageResponse,
    ) -> None:
        """Test MMS webhook processing with unified format."""
        with patch(
            "app.routers.webhooks.ReceiveSmsMmsWebhookService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_webhook = AsyncMock(
                return_value=sample_message_response
            )
            mock_service_class.return_value = mock_service

            response = client.post("/api/webhooks/sms", json=sample_mms_webhook_data)

            assert response.status_code == 200
            assert mock_service_class.called
            assert mock_service.process_webhook.called

            # Verify the service was called with the correct webhook data
            call_args = mock_service.process_webhook.call_args[0][0]
            assert call_args == sample_mms_webhook_data

    @pytest.mark.asyncio
    async def test_sms_provider_format(
        self,
        client: TestClient,
        sample_sms_provider_webhook_data: dict,
        sample_message_response: MessageResponse,
    ) -> None:
        """Test webhook processing with SMS provider format."""
        with patch(
            "app.routers.webhooks.ReceiveSmsMmsWebhookService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_webhook = AsyncMock(
                return_value=sample_message_response
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/webhooks/sms", json=sample_sms_provider_webhook_data
            )

            assert response.status_code == 200
            assert mock_service_class.called
            assert mock_service.process_webhook.called

            # Verify the service was called with the correct webhook data
            call_args = mock_service.process_webhook.call_args[0][0]
            assert call_args == sample_sms_provider_webhook_data

    @pytest.mark.asyncio
    async def test_mms_provider_format(
        self,
        client: TestClient,
        sample_mms_provider_webhook_data: dict,
        sample_message_response: MessageResponse,
    ) -> None:
        """Test webhook processing with MMS provider format."""
        with patch(
            "app.routers.webhooks.ReceiveSmsMmsWebhookService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_webhook = AsyncMock(
                return_value=sample_message_response
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/webhooks/sms", json=sample_mms_provider_webhook_data
            )

            assert response.status_code == 200
            assert mock_service_class.called
            assert mock_service.process_webhook.called

            # Verify the service was called with the correct webhook data
            call_args = mock_service.process_webhook.call_args[0][0]
            assert call_args == sample_mms_provider_webhook_data

    def test_webhook_validation_missing_from_address(self, client: TestClient) -> None:
        """Test webhook validation when from_address is missing."""
        invalid_data = {
            "to": "+12016661234",
            "body": "Test message",
            "messaging_provider_id": "message-1",
            "type": "sms",
            "timestamp": "2024-11-01T14:00:00Z",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert (
            "Invalid webhook format: missing required fields" in response_data["detail"]
        )

    def test_webhook_validation_missing_to_address(self, client: TestClient) -> None:
        """Test webhook validation when to_address is missing."""
        invalid_data = {
            "from": "+18045551234",
            "body": "Test message",
            "messaging_provider_id": "message-1",
            "type": "sms",
            "timestamp": "2024-11-01T14:00:00Z",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Missing required field: to_address" in response_data["detail"]

    def test_webhook_validation_missing_body(self, client: TestClient) -> None:
        """Test webhook validation when body is missing."""
        invalid_data = {
            "from": "+18045551234",
            "to": "+12016661234",
            "messaging_provider_id": "message-1",
            "type": "sms",
            "timestamp": "2024-11-01T14:00:00Z",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Missing required field: body" in response_data["detail"]

    def test_webhook_validation_missing_provider_message_id(
        self, client: TestClient
    ) -> None:
        """Test webhook validation when provider_message_id is missing."""
        invalid_data = {
            "from": "+18045551234",
            "to": "+12016661234",
            "body": "Test message",
            "type": "sms",
            "timestamp": "2024-11-01T14:00:00Z",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Missing required field: provider_message_id" in response_data["detail"]

    def test_webhook_validation_missing_provider_type(self, client: TestClient) -> None:
        """Test webhook validation when provider_type is missing."""
        invalid_data = {
            "from": "+18045551234",
            "to": "+12016661234",
            "body": "Test message",
            "messaging_provider_id": "message-1",
            "timestamp": "2024-11-01T14:00:00Z",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Missing required field: provider_type" in response_data["detail"]

    def test_webhook_validation_invalid_provider_type(self, client: TestClient) -> None:
        """Test webhook validation when provider_type is invalid."""
        invalid_data = {
            "from": "+18045551234",
            "to": "+12016661234",
            "body": "Test message",
            "messaging_provider_id": "message-1",
            "type": "invalid",
            "timestamp": "2024-11-01T14:00:00Z",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Invalid provider_type: invalid" in response_data["detail"]

    def test_webhook_validation_invalid_timestamp(self, client: TestClient) -> None:
        """Test webhook validation when timestamp is invalid."""
        invalid_data = {
            "from": "+18045551234",
            "to": "+12016661234",
            "body": "Test message",
            "messaging_provider_id": "message-1",
            "type": "sms",
            "timestamp": "invalid-timestamp",
        }

        response = client.post("/api/webhooks/sms", json=invalid_data)
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Invalid timestamp format" in response_data["detail"]

    def test_webhook_validation_invalid_format(self, client: TestClient) -> None:
        """Test webhook validation when format is completely invalid."""
        # Test non-dictionary input
        response = client.post("/api/webhooks/sms", json="not a dict")
        assert response.status_code == 422  # FastAPI validation error

        # Test dictionary with neither format
        response = client.post("/api/webhooks/sms", json={"some_field": "some_value"})
        assert response.status_code == 400

        response_data = response.json()
        assert "detail" in response_data
        assert "Invalid webhook format" in response_data["detail"]

    @pytest.mark.asyncio
    async def test_webhook_service_error_handling(
        self, client: TestClient, sample_sms_webhook_data: dict
    ) -> None:
        """Test webhook error handling when service raises an exception."""
        with patch(
            "app.routers.webhooks.ReceiveSmsMmsWebhookService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_webhook = AsyncMock(
                side_effect=ValueError("Service error")
            )
            mock_service_class.return_value = mock_service

            response = client.post("/api/webhooks/sms", json=sample_sms_webhook_data)

            assert response.status_code == 400
            response_data = response.json()
            assert "detail" in response_data
            assert "Service error" in response_data["detail"]

    @pytest.mark.asyncio
    async def test_webhook_unexpected_error_handling(
        self, client: TestClient, sample_sms_webhook_data: dict
    ) -> None:
        """Test webhook error handling when unexpected error occurs."""
        with patch(
            "app.routers.webhooks.ReceiveSmsMmsWebhookService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.process_webhook = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            mock_service_class.return_value = mock_service

            response = client.post("/api/webhooks/sms", json=sample_sms_webhook_data)

            assert response.status_code == 500
            response_data = response.json()
            assert "detail" in response_data
            assert "Internal server error" in response_data["detail"]

    def test_webhook_endpoint_wrong_method(self, client: TestClient) -> None:
        """Test that wrong HTTP methods return appropriate errors."""
        # GET request to POST endpoint
        response = client.get("/api/webhooks/sms")
        assert response.status_code == 405  # Method Not Allowed

    def test_webhook_endpoint_malformed_json(self, client: TestClient) -> None:
        """Test webhook endpoint with malformed JSON."""
        response = client.post(
            "/api/webhooks/sms",
            content=b"invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_webhook_endpoint_wrong_content_type(self, client: TestClient) -> None:
        """Test webhook endpoint with wrong content type."""
        response = client.post(
            "/api/webhooks/sms",
            content=b"not json",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 422
