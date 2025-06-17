-- +goose Up
-- +goose StatementBegin

-- Chats table
CREATE TABLE chats (
    id UUID PRIMARY KEY,
    title TEXT,
    assistant TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages table  
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    name TEXT,
    content TEXT, -- Nullable for tool-only messages
    tool_call_id TEXT,
    tool_call_name TEXT,
    tool_call_arguments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_tool_call CHECK (
        (role = 'tool' AND tool_call_id IS NOT NULL) OR
        (role != 'tool' AND tool_call_id IS NULL)
    )
);

-- Indexes for performance
CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_chats_updated_at ON chats(updated_at);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP INDEX IF EXISTS idx_chats_updated_at;
DROP INDEX IF EXISTS idx_messages_created_at;
DROP INDEX IF EXISTS idx_messages_chat_id;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS chats;

-- +goose StatementEnd
