import asyncio
import os
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr

from providers.cache import LRUCache

app = FastAPI(title="Mock Email Provider", description="SendGrid-like Email API")

# Configuration
MESSAGING_SERVICE_WEBHOOK_URL = os.getenv("MESSAGING_SERVICE_WEBHOOK_URL")
if not MESSAGING_SERVICE_WEBHOOK_URL:
    raise ValueError("MESSAGING_SERVICE_WEBHOOK_URL is not set")
EMAIL_PROVIDER_API_KEY = os.getenv("EMAIL_PROVIDER_API_KEY")
if not EMAIL_PROVIDER_API_KEY:
    raise ValueError("EMAIL_PROVIDER_API_KEY is not set")
SIMULATE_REPLIES = os.getenv("SIMULATE_REPLIES", "false").lower() == "true"
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))

# In-memory storage for emails (LRU cache)
# Keeps most recently accessed emails to prevent memory leaks
emails = LRUCache(max_size=CACHE_SIZE)
email_counter = 0


class EmailRequest(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    subject: str
    content: str
    html_content: Optional[str] = None


class SendGridMessage(BaseModel):
    personalizations: List[Dict]
    from_: Dict[str, str]
    subject: str
    content: List[Dict]


class SendGridResponse(BaseModel):
    message_id: str
    status: str


class IncomingEmailWebhook(BaseModel):
    from_email: EmailStr
    to_email: EmailStr
    subject: str
    content: str
    html_content: Optional[str] = None
    x_message_id: str
    timestamp: Optional[str] = None


def generate_message_id() -> str:
    """Generate a SendGrid-like message ID"""
    global email_counter
    email_counter += 1
    return f"msg_{email_counter}_{int(time.time())}"


async def trigger_email_webhook(email_data: Dict[str, Any]) -> None:
    """Trigger webhook to the main messaging service"""
    if not MESSAGING_SERVICE_WEBHOOK_URL:
        print("MESSAGING_SERVICE_WEBHOOK_URL is not configured")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                MESSAGING_SERVICE_WEBHOOK_URL,
                json=email_data,
                headers={"Content-Type": "application/json"},
            )
            print(
                f"Email webhook triggered: {response.status_code} - "
                f"{MESSAGING_SERVICE_WEBHOOK_URL}"
            )
    except Exception as e:
        print(f"Email webhook failed: {e}")


@app.post("/mail/send")
async def send_email(
    request: Request,
    background_tasks: BackgroundTasks,
    simulate_error: Optional[str] = None,
) -> Dict[str, str]:
    """Send email - simplified email provider API"""

    # Check API key in headers
    auth_header = request.headers.get("Authorization", "")
    if (
        not auth_header.startswith("Bearer ")
        or auth_header[7:] != EMAIL_PROVIDER_API_KEY
    ):
        raise HTTPException(
            status_code=401, detail={"errors": [{"message": "Invalid API key"}]}
        )

    # Parse request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Validate required fields
    if (
        "personalizations" not in body
        or "from" not in body
        or "subject" not in body
        or "content" not in body
    ):
        raise HTTPException(
            status_code=400, detail={"errors": [{"message": "Missing required fields"}]}
        )

    # Simulate error scenarios if requested
    if simulate_error:
        if simulate_error == "429":
            raise HTTPException(
                status_code=429,
                detail={
                    "errors": [
                        {"message": "Too many requests", "field": None, "help": None}
                    ]
                },
            )
        elif simulate_error == "500":
            raise HTTPException(
                status_code=500,
                detail={
                    "errors": [
                        {
                            "message": "Internal server error",
                            "field": None,
                            "help": None,
                        }
                    ]
                },
            )

    # Default scenario - success
    scenario = "delivered"

    # Generate message ID
    message_id = generate_message_id()

    # Extract email details
    to_email = body["personalizations"][0]["to"][0]["email"]
    from_email = body["from"]["email"]
    subject = body["subject"]
    content = body["content"][0]["value"]
    html_content = None
    for content_item in body["content"]:
        if content_item["type"] == "text/html":
            html_content = content_item["value"]
            break

    # Create email response
    email_response = SendGridResponse(
        message_id=message_id, status="queued" if scenario == "success" else "delivered"
    )

    # Store email
    emails[message_id] = {
        "message_id": message_id,
        "from_email": from_email,
        "to_email": to_email,
        "subject": subject,
        "content": content,
        "html_content": html_content,
        "status": email_response.status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Simulate reply email (for testing)
    if SIMULATE_REPLIES and random.choice(
        [True, False]
    ):  # 50% chance to simulate reply # nosec B311 - Test simulation code
        background_tasks.add_task(
            simulate_reply_email,
            to_email,  # Reply comes from the recipient
            from_email,  # Reply goes to the sender
            f"Re: {subject}",
            f"Thank you for your email. This is an automated reply to: "
            f"{content[:50]}...",
        )

    return {"message_id": message_id, "status": email_response.status}


async def simulate_reply_email(
    from_email: str, to_email: str, subject: str, content: str
) -> None:
    """Simulate a reply email for testing"""
    await asyncio.sleep(random.uniform(1, 5))  # Random delay # nosec B311

    reply_payload = {
        "from": from_email,
        "to": to_email,
        "xillio_id": generate_message_id(),
        "body": content,
        "attachments": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await trigger_email_webhook(reply_payload)


@app.post("/simulate/incoming")
async def simulate_incoming_email_endpoint(
    email: IncomingEmailWebhook,
) -> Dict[str, str]:
    """Simulate an incoming email for testing (calls our webhook)"""
    incoming_payload = {
        "from": email.from_email,
        "to": email.to_email,
        "xillio_id": email.x_message_id,
        "body": email.html_content or email.content,
        "attachments": [],
        "timestamp": email.timestamp or datetime.now(timezone.utc).isoformat(),
    }

    await trigger_email_webhook(incoming_payload)
    return {"status": "simulated_incoming_email", "message_id": email.x_message_id}


@app.get("/messages/{message_id}")
async def get_email(message_id: str) -> Dict[str, Any]:
    """Get email details - simplified email provider API"""
    if message_id not in emails:
        raise HTTPException(status_code=404, detail="Email not found")

    email_data = emails[message_id]
    if not isinstance(email_data, dict):
        raise HTTPException(status_code=500, detail="Invalid email data")

    return email_data


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "email_provider"}


@app.get("/emails")
async def list_emails() -> Dict[str, List[Dict[str, Any]]]:
    """List all emails (for debugging)"""
    return {"emails": list(emails.values())}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")  # nosec B104
    uvicorn.run(app, host=host, port=port)
