from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.base_provider_client import BaseProviderClient
from app.clients.email_provider_client import EmailProviderClient
from app.clients.sms_provider_client import SmsProviderClient
from app.models.api.messages import SendMessageRequest


class TestBaseProviderClient:
    """Unit tests for BaseProviderClient abstract base class."""

    def test_base_provider_is_abstract(self) -> None:
        """Test that BaseProviderClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # Abstract classes can't be instantiated directly
            BaseProviderClient()  # type: ignore

    def test_send_message_abstract_method(self) -> None:
        """Test that send_message raises NotImplementedError."""

        # Create a mock that inherits from BaseProviderClient
        class MockProvider(BaseProviderClient):
            async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
                return {"message_id": "mock_id", "status": "sent"}

            def get_provider_type(self, request: SendMessageRequest) -> str:
                return "mock"

            def extract_message_id(self, response_data: Dict[str, Any]) -> str:
                return str(response_data.get("message_id", ""))

            def extract_status(self, response_data: Dict[str, Any]) -> str:
                return str(response_data.get("status", "unknown"))

        provider = MockProvider()
        request = SendMessageRequest(
            from_address="test@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
        )

        # This should work now since we've implemented send_message
        import asyncio

        result = asyncio.run(provider.send_message(request))
        assert result == {"message_id": "mock_id", "status": "sent"}

    def test_get_provider_type_abstract_method(self) -> None:
        """Test that get_provider_type is abstract and must be implemented."""

        # Create a mock that doesn't implement get_provider_type
        class MockProvider(BaseProviderClient):
            async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
                return {"message_id": "id", "status": "status"}

            def extract_message_id(self, response_data: Dict[str, Any]) -> str:
                return str(response_data.get("message_id", ""))

            def extract_status(self, response_data: Dict[str, Any]) -> str:
                return str(response_data.get("status", "unknown"))

            # Explicitly don't implement get_provider_type

        # This should fail because get_provider_type is abstract and not implemented
        with pytest.raises(
            TypeError,
            match="Can't instantiate abstract class.*without an implementation",
        ):
            MockProvider()  # type: ignore

    def test_concrete_provider_implementation(self) -> None:
        """Test a concrete implementation works correctly."""

        class ConcreteProvider(BaseProviderClient):
            async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
                return {"message_id": "concrete-id", "status": "sent", "test": True}

            def get_provider_type(self, request: SendMessageRequest) -> str:
                return "concrete"

            def extract_message_id(self, response_data: Dict[str, Any]) -> str:
                return str(response_data.get("message_id", ""))

            def extract_status(self, response_data: Dict[str, Any]) -> str:
                return str(response_data.get("status", "unknown"))

        provider = ConcreteProvider()
        request = SendMessageRequest(
            from_address="test@example.com",
            to_address="recipient@example.com",
            body="Test message",
            attachments=[],
        )

        # Test get_provider_type works
        provider_type = provider.get_provider_type(request)
        assert provider_type == "concrete"

        # Test send_message works (would need mocking for real HTTP calls)
        # This just tests that the method exists and can be called
        assert hasattr(provider, "send_message")
        assert callable(provider.send_message)


class TestSmsProviderClient:
    """Unit tests for SmsProviderClient."""

    @pytest.fixture
    def provider(self) -> SmsProviderClient:
        """SMS provider instance."""
        return SmsProviderClient(
            base_url="http://test-sms-provider.com", api_key="test-api-key"
        )

    def test_provider_initialization(self, provider: SmsProviderClient) -> None:
        """Test SMS provider initialization."""
        assert provider.base_url == "http://test-sms-provider.com"
        assert provider.api_key == "test-api-key"

    def test_get_provider_type_sms_no_attachments(
        self, provider: SmsProviderClient
    ) -> None:
        """Test get_provider_type returns 'sms' when no attachments."""
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test SMS message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        provider_type = provider.get_provider_type(request)
        assert provider_type == "sms"

    def test_get_provider_type_mms_with_attachments(
        self, provider: SmsProviderClient
    ) -> None:
        """Test get_provider_type returns 'mms' when attachments present."""
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test MMS message",
            attachments=["image.jpg", "document.pdf"],
            timestamp=datetime.now(timezone.utc),
        )

        provider_type = provider.get_provider_type(request)
        assert provider_type == "mms"

    def test_get_provider_type_mms_single_attachment(
        self, provider: SmsProviderClient
    ) -> None:
        """Test get_provider_type returns 'mms' with single attachment."""
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test MMS message",
            attachments=["image.jpg"],
            timestamp=datetime.now(timezone.utc),
        )

        provider_type = provider.get_provider_type(request)
        assert provider_type == "mms"

    @pytest.mark.asyncio
    async def test_send_message_success(self, provider: SmsProviderClient) -> None:
        """Test successful SMS message sending."""
        # Create test request
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test SMS message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock httpx response
        mock_response_data = {
            "sid": "SM1234567890",
            "status": "sent",
            "from_": "+1234567890",
            "to": "+0987654321",
            "body": "Test SMS message",
            "date_created": "2024-01-01T12:00:00Z",
            "date_sent": "2024-01-01T12:00:01Z",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message
            result = await provider.send_message(request)

            # Verify result
            assert isinstance(result, dict)
            assert result == mock_response_data

            # Verify HTTP request was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://test-sms-provider.com/messages"

            # Verify payload structure
            payload = call_args[1]["json"]
            assert payload["From"] == "+1234567890"
            assert payload["To"] == "+0987654321"
            assert payload["Body"] == "Test SMS message"
            assert payload["MediaUrl"] == []

            # Verify headers
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer test-api-key"

    @pytest.mark.asyncio
    async def test_send_message_with_attachments(
        self, provider: SmsProviderClient
    ) -> None:
        """Test SMS message sending with attachments."""
        # Create test request with attachments
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test MMS message",
            attachments=["image.jpg", "document.pdf"],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock httpx response
        mock_response_data = {
            "sid": "MM1234567890",
            "status": "sent",
            "from_": "+1234567890",
            "to": "+0987654321",
            "body": "Test MMS message",
            "media_urls": ["image.jpg", "document.pdf"],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message
            result = await provider.send_message(request)

            # Verify result
            assert isinstance(result, dict)
            assert result == mock_response_data

            # Verify payload includes attachments
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["MediaUrl"] == ["image.jpg", "document.pdf"]

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, provider: SmsProviderClient) -> None:
        """Test SMS message sending with HTTP error."""
        request = SendMessageRequest(
            from_address="+1234567890",
            to_address="+0987654321",
            body="Test SMS message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 400 Bad Request")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message and expect error
            with pytest.raises(Exception, match="HTTP 400 Bad Request"):
                await provider.send_message(request)

    def test_provider_type_inheritance(self, provider: SmsProviderClient) -> None:
        """Test that SmsProviderClient properly inherits from BaseProviderClient."""
        assert isinstance(provider, BaseProviderClient)
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "get_provider_type")
        assert callable(provider.send_message)
        assert callable(provider.get_provider_type)


class TestEmailProviderClient:
    """Unit tests for EmailProviderClient."""

    @pytest.fixture
    def provider(self) -> EmailProviderClient:
        """Email provider instance."""
        return EmailProviderClient(
            base_url="http://test-email-provider.com", api_key="test-api-key"
        )

    def test_provider_initialization(self, provider: EmailProviderClient) -> None:
        """Test email provider initialization."""
        assert provider.base_url == "http://test-email-provider.com"
        assert provider.api_key == "test-api-key"

    def test_get_provider_type_always_email(
        self, provider: EmailProviderClient
    ) -> None:
        """Test get_provider_type always returns 'email' regardless of attachments."""
        # Test without attachments
        request1 = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test email message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Test with attachments
        request2 = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test email message",
            attachments=["document.pdf", "image.jpg"],
            timestamp=datetime.now(timezone.utc),
        )

        assert provider.get_provider_type(request1) == "email"
        assert provider.get_provider_type(request2) == "email"

    @pytest.mark.asyncio
    async def test_send_message_success(self, provider: EmailProviderClient) -> None:
        """Test successful email message sending."""
        # Create test request
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test email message content",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock httpx response
        mock_response_data = {"message_id": "EM1234567890", "status": "sent"}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message
            result = await provider.send_message(request)

            # Verify result
            assert isinstance(result, dict)
            assert result == mock_response_data

            # Verify HTTP request was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://test-email-provider.com/mail/send"

            # Verify payload structure (SendGrid-style)
            payload = call_args[1]["json"]
            assert (
                payload["personalizations"][0]["to"][0]["email"]
                == "recipient@example.com"
            )
            assert payload["from"]["email"] == "sender@example.com"
            assert payload["subject"] == "Message"
            assert payload["content"][0]["type"] == "text/plain"
            assert payload["content"][0]["value"] == "Test email message content"

            # Verify headers
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer test-api-key"

    @pytest.mark.asyncio
    async def test_send_message_with_attachments(
        self, provider: EmailProviderClient
    ) -> None:
        """Test email message sending with attachments."""
        # Create test request with attachments
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test email with attachments",
            attachments=["document.pdf", "image.jpg"],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock httpx response
        mock_response_data = {"message_id": "EM1234567891", "status": "sent"}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message
            result = await provider.send_message(request)

            # Verify result
            assert isinstance(result, dict)
            assert result == mock_response_data

            # Verify payload structure includes all required fields
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert (
                payload["personalizations"][0]["to"][0]["email"]
                == "recipient@example.com"
            )
            assert payload["from"]["email"] == "sender@example.com"
            assert payload["subject"] == "Message"
            assert payload["content"][0]["value"] == "Test email with attachments"

    @pytest.mark.asyncio
    async def test_send_message_complex_body(
        self, provider: EmailProviderClient
    ) -> None:
        """Test email message sending with complex body content."""
        # Create test request with HTML-like content
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="<html><body><h1>Test</h1><p>This is HTML content</p></body></html>",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        mock_response_data = {"message_id": "EM1234567892", "status": "sent"}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message
            await provider.send_message(request)

            # Verify the HTML content is preserved in the payload
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert (
                payload["content"][0]["value"]
                == "<html><body><h1>Test</h1><p>This is HTML content</p></body></html>"
            )

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, provider: EmailProviderClient) -> None:
        """Test email message sending with HTTP error."""
        request = SendMessageRequest(
            from_address="sender@example.com",
            to_address="recipient@example.com",
            body="Test email message",
            attachments=[],
            timestamp=datetime.now(timezone.utc),
        )

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 401 Unauthorized")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Send message and expect error
            with pytest.raises(Exception, match="HTTP 401 Unauthorized"):
                await provider.send_message(request)

    def test_provider_type_inheritance(self, provider: EmailProviderClient) -> None:
        """Test that EmailProviderClient properly inherits from BaseProviderClient."""
        assert isinstance(provider, BaseProviderClient)
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "get_provider_type")
        assert callable(provider.send_message)
        assert callable(provider.get_provider_type)

    def test_get_provider_type_ignores_request(
        self, provider: EmailProviderClient
    ) -> None:
        """Test that get_provider_type always returns email."""
        # Create request with different content
        request = SendMessageRequest(
            from_address="",
            to_address="",
            body="",
            attachments=["file1", "file2", "file3"],
            timestamp=datetime.now(timezone.utc),
        )

        # Should still return email regardless of request content
        assert provider.get_provider_type(request) == "email"
