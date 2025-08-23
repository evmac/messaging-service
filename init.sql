-- Database initialization script for messaging service
-- This script runs when the PostgreSQL container starts up

-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Conversations table
-- Groups messages between participants
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
-- Stores individual messages from SMS/MMS and Email providers
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Provider information
    provider_type VARCHAR(20) NOT NULL CHECK (provider_type IN ('sms', 'mms', 'email')),
    provider_message_id VARCHAR(255), -- External provider's message ID
    
    -- Message participants
    from_address VARCHAR(255) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    
    -- Message content
    body TEXT NOT NULL,
    attachments JSONB DEFAULT '[]', -- Array of attachment URLs
    
    -- Message metadata
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
    
    -- Timestamps
    message_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Participants table
-- Tracks who is involved in each conversation
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    address VARCHAR(255) NOT NULL, -- Phone number or email address
    address_type VARCHAR(10) NOT NULL CHECK (address_type IN ('phone', 'email')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(message_timestamp DESC);
CREATE INDEX idx_messages_provider_id ON messages(provider_message_id);
CREATE INDEX idx_messages_participants ON messages(from_address, to_address);
CREATE INDEX idx_participants_conversation ON participants(conversation_id);
CREATE INDEX idx_participants_address ON participants(address);

-- Unique constraint to prevent duplicate participants per conversation
CREATE UNIQUE INDEX idx_unique_participant_conversation 
ON participants(conversation_id, address);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_conversations_updated_at 
    BEFORE UPDATE ON conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at 
    BEFORE UPDATE ON messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
