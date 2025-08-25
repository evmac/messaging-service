from typing import Any, Dict

import httpx

from app.clients.base_provider_client import BaseProviderClient
from app.models.api.messages import SendMessageRequest


class SmsProviderClient(BaseProviderClient):
    """SMS/MMS provider client using httpx."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def send_message(self, request: SendMessageRequest) -> Dict[str, Any]:
        """Send SMS or MMS message via provider API."""
        # Transform SendMessageRequest to SMS provider format
        payload = {
            "From": request.from_address,
            "To": request.to_address,
            "Body": request.body,
            "MediaUrl": request.attachments or [],
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages", json=payload, headers=headers
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            return data

    def get_provider_type(self, request: SendMessageRequest) -> str:
        """Return 'mms' if attachments present, otherwise 'sms'."""
        return "mms" if request.attachments else "sms"

    def extract_message_id(self, response_data: Dict[str, Any]) -> str:
        """Extract message ID from Twilio-style response."""
        return str(response_data.get("sid", ""))

    def extract_status(self, response_data: Dict[str, Any]) -> str:
        """Extract and normalize status from Twilio-style response."""
        status = str(response_data.get("status", "unknown"))

        # Normalize Twilio status to our standard statuses
        status_mapping = {
            "queued": "pending",
            "sending": "pending",
            "sent": "sent",
            "delivered": "delivered",
            "undelivered": "failed",
            "failed": "failed",
        }

        return status_mapping.get(status, "unknown")
