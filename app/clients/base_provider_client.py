from abc import ABC, abstractmethod
from typing import Any, Dict

from app.models.api.messages import SendMessageRequest


class BaseProviderClient(ABC):
    """Abstract base class for message providers."""

    @abstractmethod
    async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
        """Send message and return provider response data.

        Returns:
            Dict containing the raw provider response data.
            Each provider handles its own response format.
        """

    @abstractmethod
    def get_provider_type(self, request: SendMessageRequest) -> str:
        """Return provider type: 'sms', 'mms', or 'email'."""

    @abstractmethod
    def extract_message_id(self, response_data: Dict[str, Any]) -> str:
        """Extract the provider message ID from the response data.

        Args:
            response_data: Raw response data from the provider

        Returns:
            The provider's message ID
        """

    @abstractmethod
    def extract_status(self, response_data: Dict[str, Any]) -> str:
        """Extract the message status from the response data.

        Args:
            response_data: Raw response data from the provider

        Returns:
            Normalized status ('sent', 'pending', 'failed', etc.)
        """
