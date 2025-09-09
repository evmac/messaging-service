# Backend Interview Project

This is a scaffold for Hatch's backend interview project. It includes basic setup for development, testing, and deployment.

## Guidelines

At Hatch, we work with several message providers to offer a unified way for our Customers to  communicate to their Contacts. Today we offer SMS, MMS, email, voice calls, and voicemail drops. Your task is to implement an HTTP service that supports the core messaging functionality of Hatch, on a much smaller scale. Specific instructions and guidelines on completing the project are below.

### General Guidelines

- You may use whatever programming language, libraries, or frameworks you'd like. 
- We strongly encourage you to use whatever you're most familiar with so that you can showcase your skills and know-how. Candidates will not receive any kind of 'bonus points' or 'red flags' regarding their specific choices of language.
- You are welcome to use AI, Google, StackOverflow, etc as resources while you're developing. We just ask that you understand the code very well, because we will continue developing on it during your onsite interview.
- For ease of assessment, we strongly encourage you to use the `start.sh` script provided in the `bin/` directory, and implement it to run your service. We will run this script to start your project during our assessment. 

### Project-specific guidelines

- Assume that a provider may return HTTP error codes like 500, 429 and plan accordingly
- Conversations consist of messages from multiple providers. Feel free to consult providers such as Twilio or Sendgrid docs when designing your solution, but all external resources should be mocked out by your project. We do not expect you to actually integrate with a third party provider as part of this project.
- It's OK to use Google or a coding assistant to produce your code. Just make sure you know it well, because the next step will be to code additional features in this codebase with us during your full interview.

## Requirements

The service should implement:

- **Unified Messaging API**: HTTP endpoints to send and receive messages from both SMS/MMS and Email providers
  - Support sending messages through the appropriate provider based on message type
  - Handle incoming webhook messages from both providers
- **Conversation Management**: Messages should be automatically grouped into conversations based on participants (from/to addresses)
- **Data Persistence**: All conversations and messages must be stored in a relational database with proper relationships and indexing

## Database & Migrations

### Database Setup

The project uses PostgreSQL as the relational database with SQLAlchemy ORM for data persistence. The database schema includes:

- **Conversations**: Groups messages between participants
- **Messages**: Individual messages from SMS/MMS and Email providers
- **Participants**: Tracks who is involved in each conversation

Database schema is managed through **Alembic migrations** (managed separately from the application):
- Table creation and modification
- Indexes and constraints
- PostgreSQL functions and triggers
- Proper dependency ordering (functions before triggers, etc.)

**Important**: The main application is **agnostic of migrations** - it simply connects to whatever database schema exists. Migrations are managed as a separate deployment/infrastructure concern.

### Migration Strategy

Database migrations are managed using **Alembic**, SQLAlchemy's official migration tool. The migration system provides:

- **Version Control**: Track all database schema changes
- **Environment Safety**: Safe migrations across development, staging, and production
- **Rollback Support**: Ability to downgrade if issues arise
- **Team Collaboration**: Migrations as code that can be reviewed

#### Migration Commands

Use the provided Makefile commands for easier migration management:

```bash
# Create new migration from model changes (interactive)
make migrate-new

# Upgrade database to latest migration
make migrate-up

# Downgrade database to base (removes all migrations)
make migrate-down

# Show current migration version
make migrate-current

# Show migration history
make migrate-history

# Check for pending model changes
make migrate-check
```

#### Migration Workflow

**⚠️ Important**: Migrations are managed **separately from the application**. Run these commands **before** starting the application:

1. **Make model changes** in your SQLAlchemy models (e.g., `app/models/db/*.py`)
2. **Generate migration**: `make migrate-new` (enter a descriptive message)
3. **Review the generated migration** in `migrations/versions/`
4. **Apply migration**: `make migrate-up`
5. **Verify**: `make migrate-current`

**Note**: The initial schema migration creates all necessary tables, indexes, functions, and triggers in the correct dependency order. Subsequent migrations will handle any schema changes.

**Application Startup**: The application simply connects to whatever database schema exists - it has no knowledge of or dependency on migrations.

### Database Configuration

Alembic automatically loads environment variables from a `.env` file if it exists in the project root. This makes configuration easier and more secure.

**Option 1: Using .env file (Recommended)**

Create a `.env` file in the project root:

```bash
# .env
DATABASE_URL=postgresql+asyncpg://messaging_user:messaging_password@localhost:5432/messaging_service
SQL_DEBUG=false
```

Alembic will automatically load this file when running migrations.

**Option 2: Environment Variables**

Set environment variables directly:

```bash
export DATABASE_URL="postgresql+asyncpg://messaging_user:messaging_password@localhost:5432/messaging_service"
export SQL_DEBUG=false
```

**Option 3: Makefile Commands**

The provided Makefile commands handle database operations:

```bash
make migrate-current    # Check current migration status
make migrate-new        # Create new migration (interactive)
make migrate-up         # Apply all migrations
make migrate-down       # Rollback migrations
make migrate-history    # View migration history
```

### Environment Variables

```bash
# Database connection (required)
DATABASE_URL=postgresql+asyncpg://messaging_user:messaging_password@localhost:5432/messaging_service

# Debug logging (optional)
SQL_DEBUG=false
```

### Providers

**SMS & MMS**

**Example outbound payload to send an SMS or MMS**

```json
{
    "from": "from-phone-number",
    "to": "to-phone-number",
    "type": "mms" | "sms",
    "body": "text message",
    "attachments": ["attachment-url"] | [] | null,
    "timestamp": "2024-11-01T14:00:00Z" // UTC timestamp
}
```

**Example inbound SMS**

```json
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "sms",
    "messaging_provider_id": "message-1",
    "body": "text message",
    "attachments": null,
    "timestamp": "2024-11-01T14:00:00Z" // UTC timestamp
}
```

**Example inbound MMS**

```json
{
    "from": "+18045551234",
    "to": "+12016661234",
    "type": "mms",
    "messaging_provider_id": "message-2",
    "body": "text message",
    "attachments": ["attachment-url"] | [],
    "timestamp": "2024-11-01T14:00:00Z" // UTC timestamp
}
```

**Email Provider**

**Example Inbound Email**

```json
{
    "from": "[user@usehatchapp.com](mailto:user@usehatchapp.com)",
    "to": "[contact@gmail.com](mailto:contact@gmail.com)",
    "xillio_id": "message-2",
    "body": "<html><body>html is <b>allowed</b> here </body></html>",  "attachments": ["attachment-url"] | [],
    "timestamp": "2024-11-01T14:00:00Z" // UTC timestamp
}
```

**Example Email Payload**

```json
{
    "from": "[user@usehatchapp.com](mailto:user@usehatchapp.com)",
    "to": "[contact@gmail.com](mailto:contact@gmail.com)",
    "body": "text message with or without html",
    "attachments": ["attachment-url"] | [],
    "timestamp": "2024-11-01T14:00:00Z" // UTC timestamp
}
```

### Project Structure

This project structure is laid out for you already. You are welcome to move or change things, just update the Makefile, scripts, and/or docker resources accordingly. As part of the evaluation of your code, we will run 

```
.
├── bin/                    # Scripts and executables
│   ├── start.sh           # Application startup script
│   └── test.sh            # API testing script with curl commands
├── docker-compose.yml      # PostgreSQL database setup
├── Makefile               # Build and development commands with docker-compose integration
└── README.md              # This file
```

## Getting Started

1. Clone the repository
2. Run `make setup` to initialize the project
3. Run `docker-compose up -d` to start the PostgreSQL database, or modify it to choose a database of your choice
4. Run `make run` to start the application
5. Run `make test` to run tests

## Development

- Use `docker-compose up -d` to start the PostgreSQL database
- Use `make run` to start the development server
- Use `make test` to run tests
- Use `docker-compose down` to stop the database

## Database

The application uses PostgreSQL as its database. The docker-compose.yml file sets up:
- PostgreSQL 15 with Alpine Linux
- Database: `messaging_service`
- User: `messaging_user`
- Password: `messaging_password`
- Port: `5432` (exposed to host)

To connect to the database directly:
```bash
docker-compose exec postgres psql -U messaging_user -d messaging_service
```

Again, you are welcome to make changes here, as long as they're in the docker-compose.yml

## Mock Provider Services

The project includes mock implementations of SMS/MMS and Email providers for development and testing:

See more in [the README](providers/README.md).

### SMS/MMS Provider
- **Port**: 8001 (localhost)
- **API**: SMS/MMS provider compatible API
- **Features**: Send SMS/MMS, simulate errors, trigger webhooks

### Email Provider
- **Port**: 8002 (localhost)
- **API**: Email provider compatible API
- **Features**: Send emails, simulate errors, trigger webhooks
