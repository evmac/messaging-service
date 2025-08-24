# Messaging Service - Project Index

## 📁 Project Structure Overview

```
messaging-service/
├── .github/                      # Github workflows and repository management
├── app/                          # Main application code
│   ├── models/                   # Application data models
│   │   ├── __init__.py
|   |   ├── api/                 # Pydantic API contracts
│   │   |   ├── __init__.py
│   │   |   ├── conversations.py
│   │   |   ├── messages.py
│   │   |   └── participants.py
│   │   └── sql/                 # SQLAlchemy database schema
│   │       ├── __init__.py
│   │       ├── conversation.py
│   │       ├── message.py
│   │       └── participant.py
│   ├── repositories/            # Data access layer
│   │   ├── __init__.py
│   │   ├── base_repository.py   # Base repository patterns
│   │   ├── conversation_repository.py
│   │   ├── message_repository.py
│   │   └── participant_repository.py
│   ├── services/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── send_message_service.py
│   │   ├── receive_sms_mms_webhook_service.py
│   │   ├── receive_email_webhook_service.py
│   │   ├── list_conversations_service.py
│   │   └── get_conversation_messages_service.py
│   ├── routers/                 # HTTP API layer
│   │   ├── __init__.py
│   │   ├── messages.py         # Send message endpoints
│   │   ├── conversations.py    # Conversation management
│   │   └── webhooks.py         # Webhook processing
│   ├── database.py             # Database configuration
│   └── main.py                 # FastAPI application
├── providers/                  # Mock provider services
|   ├── base_provider.py        # Base provider patterns
│   ├── sms_provider.py         # Twilio-like SMS/MMS provider
│   ├── email_provider.py       # SendGrid-like email provider
│   ├── cache.py                # LRU cache implementation
│   └── Dockerfile.*            # Provider container configs
├── doc/                        # Documentation
│   ├── prd-feature-001-core-data-layer.md
│   ├── prd-feature-002-send-message-service.md
│   ├── prd-feature-003-sms-mms-webhook-processing.md
│   ├── prd-feature-004-email-webhook-processing.md
│   ├── prd-feature-005-list-conversations.md
│   └── prd-feature-006-get-conversation-messages.md
├── tests/                      # Test suite
│   ├── mocks/                  # Test mocks
│   ├── test_database.py        # Database tests
│   ├── test_main.py            # Application tests
│   └── conftest.py             # Test configuration
├── bin/                        # Executable scripts
│   ├── start.sh                # Application startup
│   └── test.sh                 # API testing script
├── lib/                        # Common utilities
├── venv/                       # Python virtual environment - not preserved in source control
├── docker-compose.yml          # Database setup
├── init.sql                    # Database schema
├── requirements*.txt           # Python dependencies
├── pyproject.toml              # Project configuration
├── Makefile                    # Development commands
└── README.md                   # Project documentation
```

## 🏗️ Architecture Overview

### Clean Architecture Layers

1. **HTTP Layer** (`app/routers/`)
   - FastAPI route handlers
   - Request/response transformation
   - HTTP-specific concerns (status codes, headers)
   - Input validation and serialization

2. **Business Logic Layer** (`app/services/`)
   - Core business operations
   - Provider integration
   - Conversation management
   - Error handling and retry logic
   - Works with Pydantic models

3. **Data Access Layer** (`app/repositories/`)
   - Database operations
   - SQLAlchemy model management
   - Pydantic ↔ SQLAlchemy translation
   - Query optimization

4. **Data Models** (`app/models/`)
   - **Pydantic Models**: API contracts and validation
   - **SQLAlchemy Models**: Database schema definitions

### Key Design Principles

- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Inversion**: Services depend on abstractions, not concretions
- **Testability**: Business logic isolated from HTTP and database concerns
- **Type Safety**: Extensive use of Python typing and Pydantic validation
- **Provider Abstraction**: Easy to swap providers without changing business logic

## 🚀 Development Workflow

### 1. Feature Implementation Order
```
Feature 1 → Feature 2 → Feature 3 → Feature 4 → Feature 5 → Feature 6
```

### 2. Testing Strategy
- **Unit Tests**: Business logic in services (no external dependencies)
- **Integration Tests**: Database operations and API endpoints
- **End-to-End Tests**: Full request/response cycles

### 3. Database Management
- **Schema**: Defined in `init.sql`
- **Migrations**: Handled by SQLAlchemy (future)
- **Connection**: Async PostgreSQL with connection pooling

## 📋 Feature Status

- ✅ **Feature 1**: Core Data Layer (Foundation)
- ⏳ **Feature 2**: Send Message Service (In Progress)
- 📋 **Feature 3**: SMS/MMS Webhook Processing (Planned)
- 📋 **Feature 4**: Email Webhook Processing (Planned)
- 📋 **Feature 5**: List Conversations (Planned)
- 📋 **Feature 6**: Get Conversation Messages (Planned)

## 🔧 Development Commands

```bash
# Setup and run
make setup          # Initialize environment
make run           # Start development server
make test          # Run test suite

# Database
docker-compose up -d  # Start PostgreSQL
docker-compose exec postgres psql -U messaging_user -d messaging_service

# Code quality
make lint          # Run linters
make format        # Format code
```

## 🎯 API Endpoints

### Send Messages
- `POST /api/messages/sms` - Send SMS/MMS
- `POST /api/messages/email` - Send Email

### Webhooks
- `POST /api/webhooks/sms` - Receive SMS/MMS
- `POST /api/webhooks/email` - Receive Email

### Conversations
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{id}/messages` - Get conversation messages

## 📚 Key Technologies

- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Async database ORM
- **Pydantic**: Data validation and serialization
- **PostgreSQL**: Relational database
- **Docker**: Containerized providers
- **httpx**: Async HTTP client for providers
