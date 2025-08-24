import asyncio
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from providers.cache import LRUCache

app = FastAPI(title="Mock SMS/MMS Provider", description="Twilio-like SMS/MMS API")

# Configuration
MESSAGING_SERVICE_WEBHOOK_URL = os.getenv("MESSAGING_SERVICE_WEBHOOK_URL")
if not MESSAGING_SERVICE_WEBHOOK_URL:
    raise ValueError("MESSAGING_SERVICE_WEBHOOK_URL is not set")
SMS_PROVIDER_API_KEY = os.getenv("SMS_PROVIDER_API_KEY")
if not SMS_PROVIDER_API_KEY:
    raise ValueError("SMS_PROVIDER_API_KEY is not set")
SIMULATE_REPLIES = os.getenv("SIMULATE_REPLIES", "false").lower() == "true"
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))

# In-memory storage for messages (LRU cache)
# Keeps most recently accessed messages to prevent memory leaks
messages = LRUCache(max_size=CACHE_SIZE)
message_counter = 0


class MessageRequest(BaseModel):
    From: str
    To: str
    Body: str
    MediaUrl: Optional[List[str]] = None


class MessageResponse(BaseModel):
    sid: str
    from_: str
    to: str
    body: str
    status: str
    date_created: str
    date_sent: Optional[str] = None
    media_urls: Optional[List[str]] = None


class IncomingWebhookPayload(BaseModel):
    From: str
    To: str
    Body: str
    MessageSid: str
    MediaUrl: Optional[List[str]] = None
    Timestamp: Optional[str] = None


def generate_message_sid() -> str:
    """Generate a Twilio-like message SID"""
    global message_counter
    message_counter += 1
    return "MM" + str(message_counter).zfill(32)


def determine_message_type(media_urls: Optional[List[str]] = None) -> str:
    """Determine if message is SMS or MMS based on media"""
    if media_urls and len(media_urls) > 0:
        return "mms"
    return "sms"


async def trigger_webhook(message_data: Dict[str, Any]) -> None:
    """Trigger webhook to the main messaging service"""
    if not MESSAGING_SERVICE_WEBHOOK_URL:
        print("MESSAGING_SERVICE_WEBHOOK_URL is not configured")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                MESSAGING_SERVICE_WEBHOOK_URL,
                json=message_data,
                headers={"Content-Type": "application/json"},
            )
            print(
                f"Webhook triggered: {response.status_code} - "
                f"{MESSAGING_SERVICE_WEBHOOK_URL}"
            )
    except Exception as e:
        print(f"Webhook failed: {e}")


@app.post("/messages")
async def send_message(
    message: MessageRequest,
    background_tasks: BackgroundTasks,
    simulate_error: Optional[str] = None,
) -> MessageResponse:
    """Send SMS/MMS message - simplified SMS provider API"""

    # Simulate error scenarios if requested
    if simulate_error:
        if simulate_error == "429":
            raise HTTPException(
                status_code=429, detail="Too Many Requests - Rate limit exceeded"
            )
        elif simulate_error == "500":
            raise HTTPException(
                status_code=500,
                detail="Internal Server Error - Provider temporarily unavailable",
            )

    # Default scenario - success
    scenario = "delivered"

    # Generate message SID
    message_sid = generate_message_sid()

    # Create message response
    message_response = MessageResponse(
        sid=message_sid,
        from_=message.From,
        to=message.To,
        body=message.Body,
        status="queued" if scenario == "success" else "delivered",
        date_created=datetime.now(timezone.utc).isoformat(),
        date_sent=(
            datetime.now(timezone.utc).isoformat() if scenario == "delivered" else None
        ),
        media_urls=message.MediaUrl,
    )

    # Store message
    messages[message_sid] = message_response.dict()

    # Simulate webhook for incoming message (for testing)
    if random.choice([True, False]):  # nosec B311
        background_tasks.add_task(
            simulate_incoming_message,
            message.To,  # Reply comes from the recipient
            message.From,  # Reply goes to the sender
            f"Reply to: {message.Body[:50]}...",
        )

    return message_response


async def simulate_incoming_message(
    from_number: str, to_number: str, body: str
) -> None:
    """Simulate an incoming message for testing"""
    await asyncio.sleep(random.uniform(1, 5))  # Random delay # nosec B311

    incoming_payload = {
        "from": from_number,
        "to": to_number,
        "type": "sms",
        "messaging_provider_id": generate_message_sid(),
        "body": body,
        "attachments": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await trigger_webhook(incoming_payload)


@app.get("/messages/{message_sid}")
async def get_message(message_sid: str) -> Dict[str, Any]:
    """Get message details - simplified SMS provider API"""

    if message_sid not in messages:
        raise HTTPException(status_code=404, detail="Message not found")

    message_data = messages[message_sid]
    if not isinstance(message_data, dict):
        raise HTTPException(status_code=500, detail="Invalid message data")

    return message_data


@app.post("/simulate/incoming")
async def simulate_incoming_message_endpoint(
    payload: IncomingWebhookPayload,
) -> Dict[str, str]:
    """Simulate an incoming message for testing (calls our webhook)"""
    incoming_payload = {
        "from": payload.From,
        "to": payload.To,
        "type": determine_message_type(payload.MediaUrl),
        "messaging_provider_id": payload.MessageSid,
        "body": payload.Body,
        "attachments": payload.MediaUrl,
        "timestamp": payload.Timestamp or datetime.now(timezone.utc).isoformat(),
    }

    await trigger_webhook(incoming_payload)
    return {"status": "simulated_incoming_message", "message_sid": payload.MessageSid}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "sms_provider"}


@app.get("/messages")
async def list_messages() -> Dict[str, List[Dict[str, Any]]]:
    """List all messages (for debugging)"""
    return {"messages": list(messages.values())}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")  # nosec B104
    uvicorn.run(app, host=host, port=port)
