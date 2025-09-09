"""create initial schema

Revision ID: 0d22580b00df
Revises: 106672ee9542
Create Date: 2025-08-26 00:34:38.666219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0d22580b00df'
down_revision: Union[str, Sequence[str], None] = '106672ee9542'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create the function (required before triggers)
    op.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    ''')

    # Step 2: Create tables (skip if they already exist from init.sql)
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            provider_type VARCHAR(20) NOT NULL CHECK (provider_type IN ('sms', 'mms', 'email')),
            provider_message_id VARCHAR(255),
            from_address VARCHAR(255) NOT NULL,
            to_address VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            attachments JSONB DEFAULT '[]'::jsonb,
            direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
            message_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            address VARCHAR(255) NOT NULL,
            address_type VARCHAR(10) NOT NULL CHECK (address_type IN ('phone', 'email')),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Step 3: Create indexes (skip if they already exist)
    op.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(message_timestamp DESC)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_messages_provider_id ON messages(provider_message_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_messages_participants ON messages(from_address, to_address)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_participants_conversation ON participants(conversation_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_participants_address ON participants(address)')
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_participant_conversation ON participants(conversation_id, address)')

    # Step 4: Create triggers (only after tables exist)
    op.execute('''
        CREATE TRIGGER update_conversations_updated_at
            BEFORE UPDATE ON conversations
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    ''')

    op.execute('''
        CREATE TRIGGER update_messages_updated_at
            BEFORE UPDATE ON messages
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    ''')


def downgrade() -> None:
    """Downgrade schema."""
    # For a baseline migration, we don't drop tables on downgrade
    # to avoid data loss. In a production system, you would implement
    # proper downgrade logic if needed.
    pass
