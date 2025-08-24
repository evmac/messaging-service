# Mock Provider Services

This directory contains mock implementations of SMS/MMS and Email providers for development and testing.

## Services

### SMS/MMS Provider
- **Port**: 8001
- **API**: Simple SMS/MMS provider API
- **Features**:
  - Send SMS/MMS messages via `POST /messages`
  - Retrieve message details via `GET /messages/{id}`
  - Simulate various HTTP status codes (200, 429, 500)
  - Test endpoint to simulate incoming messages

### Email Provider
- **Port**: 8002
- **API**: Simple email provider API
- **Features**:
  - Send emails via `POST /mail/send`
  - Retrieve email details via `GET /messages/{id}`
  - Simulate various HTTP status codes (200, 429, 500)
  - Test endpoint to simulate incoming emails

## Usage

### Starting Services

```bash
# Build the provider services
make providers-build

# Start the provider services
make providers-up

# View logs
make providers-logs

# Stop the provider services
make providers-down
```

### Testing the SMS Provider

```bash
# Send an SMS
curl -X POST "http://localhost:8001/messages" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=%2B1234567890&To=%2B0987654321&Body=Hello%20World"

# Send an SMS with rate limit error simulation
curl -X POST "http://localhost:8001/messages?simulate_error=429" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=%2B1234567890&To=%2B0987654321&Body=Hello%20World"

# Get message details
curl -X GET "http://localhost:8001/messages/MM1234567890"

# Simulate an incoming SMS (calls our webhook)
curl -X POST "http://localhost:8001/simulate/incoming" \
  -H "Content-Type: application/json" \
  -d '{
    "From": "+1234567890",
    "To": "+0987654321",
    "Body": "Reply message",
    "MessageSid": "MM1234567890"
  }'

# Check health
curl http://localhost:8001/health
```

### Testing the Email Provider

```bash
# Send an email
curl -X POST "http://localhost:8002/mail/send" \
  -H "Authorization: Bearer email_provider_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [{
      "to": [{"email": "recipient@example.com"}]
    }],
    "from": {"email": "sender@example.com"},
    "subject": "Test Email",
    "content": [{
      "type": "text/plain",
      "value": "Test email content"
    }]
  }'

# Send an email with server error simulation
curl -X POST "http://localhost:8002/mail/send?simulate_error=500" \
  -H "Authorization: Bearer email_provider_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [{
      "to": [{"email": "recipient@example.com"}]
    }],
    "from": {"email": "sender@example.com"},
    "subject": "Test Email",
    "content": [{
      "type": "text/plain",
      "value": "Test email content"
    }]
  }'

# Get email details
curl -X GET "http://localhost:8002/messages/msg_1234567890"

# Simulate an incoming email (calls our webhook)
curl -X POST "http://localhost:8002/simulate/incoming" \
  -H "Content-Type: application/json" \
  -d '{
    "from_email": "reply@example.com",
    "to_email": "sender@example.com",
    "subject": "Re: Test Email",
    "content": "This is a reply",
    "x_message_id": "msg_1234567890"
  }'

# Check health
curl http://localhost:8002/health
```

## Configuration

Environment variables can be configured in a `.env` file (copy from `config.env.example`):

```bash
cp config.env.example .env
```

### Key Environment Variables

- `MESSAGING_SERVICE_URL`: URL of the main messaging service for webhooks
- `SMS_PROVIDER_API_KEY`: API key for SMS provider authentication
- `EMAIL_PROVIDER_API_KEY`: API key for email provider authentication

## Error Simulation

Both providers support optional error simulation per-request using the `simulate_error` query parameter:
- **Success** (200): Default behavior - message queued or delivered
- **Rate Limit** (429): Add `?simulate_error=429` to the request
- **Server Error** (500): Add `?simulate_error=500` to the request

Example:
```bash
# Normal request
curl -X POST "http://localhost:8001/messages" -d "From=+1234567890&To=+0987654321&Body=Hello"

# Simulate rate limit error
curl -X POST "http://localhost:8001/messages?simulate_error=429" -d "From=+1234567890&To=+0987654321&Body=Hello"
```

## Simulation Endpoints

For testing purposes, both providers include simulation endpoints that call your webhooks:

- `POST /simulate/incoming` - SMS provider calls your `/webhooks/sms/incoming`
- `POST /simulate/incoming` - Email provider calls your `/webhooks/email/incoming`

These endpoints are for testing only - they simulate what would happen if real external SMS/email providers sent messages to you.

The webhook payload format matches the specification in the main project README.
