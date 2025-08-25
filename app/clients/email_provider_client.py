from typing import Any, Dict

import httpx

from app.clients.base_provider_client import BaseProviderClient
from app.models.api.messages import SendMessageRequest


class EmailProviderClient(BaseProviderClient):
    """Email provider client using httpx."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
        """Send email message via provider API."""
        # Transform SendMessageRequest to SendGrid-style payload
        payload = {
            "personalizations": [{"to": [{"email": request.to_address}]}],
            "from": {"email": request.from_address},
            "subject": "Message",  # Could be extracted from body or made configurable
            "content": [{"type": "text/plain", "value": request.body}],
        }

        # Add attachments if present
        if request.attachments:
            # Note: This is a simplified attachment handling
            # In a real implementation, you'd need to handle file uploads
            # and convert them to the provider's expected format
            pass

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mail/send", json=payload, headers=headers
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            return data

    def get_provider_type(self, _: SendMessageRequest) -> str:
        """Return 'email'."""
        return "email"

    def extract_message_id(self, response_data: Dict[str, Any]) -> str:
        """Extract message ID from SendGrid-style response."""
        return str(response_data.get("message_id", ""))

    def extract_status(self, response_data: Dict[str, Any]) -> str:
        """Extract and normalize status from SendGrid-style response."""
        status = str(response_data.get("status", "unknown"))

        # Normalize SendGrid status to our standard statuses
        status_mapping = {
            "pending": "pending",
            "processed": "sent",
            "dropped": "failed",
            "deferred": "pending",
            "bounce": "failed",
            "delivered": "delivered",
            "blocked": "failed",
        }

        return status_mapping.get(status, "unknown")
