package models

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/google/uuid"
)

// MessageRole represents the role of a message
type MessageRole string

const (
	RoleUser      MessageRole = "user"
	RoleAssistant MessageRole = "assistant"
	RoleTool      MessageRole = "tool"
)

// ToolCall represents a tool call in a message
type ToolCall struct {
	ID        string `json:"id"`
	Name      string `json:"name"`      // Function name
	Arguments string `json:"arguments"` // Serialized JSON
}

// Message represents a chat message
type Message struct {
	ID         string     `json:"id"`
	Role       MessageRole `json:"role"`
	Name       *string    `json:"name,omitempty"`       // Name of the assistant
	Content    string     `json:"content"`
	ToolCall   *ToolCall  `json:"tool_call,omitempty"`   // Only set if role is "assistant"
	ToolCallID *string    `json:"tool_call_id,omitempty"` // Only set if role is "tool"
}

// NewMessage creates a new message with a generated ID
func NewMessage(role MessageRole, content string) *Message {
	return &Message{
		ID:      generateMessageID(),
		Role:    role,
		Content: content,
	}
}

// ChatState represents the persistent state of a chat
type ChatState struct {
	ID        string     `json:"id"`
	Messages  []*Message `json:"messages"`
	Assistant *string    `json:"assistant,omitempty"`
	Title     *string    `json:"title,omitempty"`
}

// NewChatState creates a new chat state
func NewChatState(id, assistant string) *ChatState {
	return &ChatState{
		ID:        id,
		Messages:  make([]*Message, 0),
		Assistant: &assistant,
	}
}

// CreateNew creates a new chat state with generated ID
func CreateNew(assistant string) *ChatState {
	return NewChatState(generateChatID(), assistant)
}

// LoadFromDisk loads a chat state from disk
func LoadFromDisk(chatID string) (*ChatState, error) {
	filePath := FilePath(chatID)
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read chat file: %w", err)
	}

	var state ChatState
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("failed to unmarshal chat state: %w", err)
	}

	return &state, nil
}

// SaveToDisk saves the chat state to disk
func (cs *ChatState) SaveToDisk() error {
	chatsDir := getChatsDirectory()
	if err := os.MkdirAll(chatsDir, 0755); err != nil {
		return fmt.Errorf("failed to create chats directory: %w", err)
	}

	data, err := json.MarshalIndent(cs, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal chat state: %w", err)
	}

	filePath := FilePath(cs.ID)
	if err := os.WriteFile(filePath, data, 0644); err != nil {
		return fmt.Errorf("failed to write chat file: %w", err)
	}

	return nil
}

// FilePath returns the file path for a chat ID
func FilePath(id string) string {
	return filepath.Join(getChatsDirectory(), fmt.Sprintf("%s.json", id))
}

// getChatsDirectory returns the chats directory path
func getChatsDirectory() string {
	if dir := os.Getenv("CHATS_DIR"); dir != "" {
		return dir
	}
	return "chats"
}

// Reply represents a streaming message builder
type Reply struct {
	chat    *Chat
	Message *Message
}

// NewReply creates a new reply
func NewReply(chat *Chat, role MessageRole, name string) *Reply {
	return &Reply{
		chat: chat,
		Message: &Message{
			ID:      generateMessageID(),
			Role:    role,
			Name:    &name,
			Content: "",
		},
	}
}

// FieldType represents the field being updated in a streaming response
type FieldType string

const (
	FieldContent           FieldType = "content"
	FieldToolCallID        FieldType = "tool_call.id"
	FieldToolCallName      FieldType = "tool_call.name"
	FieldToolCallArguments FieldType = "tool_call.arguments"
	FieldToolCallIDDirect  FieldType = "tool_call_id"
)

// AddChunk adds a chunk to the reply
func (r *Reply) AddChunk(chunk string, field FieldType) error {
	switch field {
	case FieldContent:
		r.Message.Content += chunk
	case FieldToolCallIDDirect:
		r.Message.ToolCallID = &chunk
	case FieldToolCallID:
		if r.Message.ToolCall == nil {
			r.Message.ToolCall = &ToolCall{}
		}
		r.Message.ToolCall.ID = chunk
	case FieldToolCallName:
		if r.Message.ToolCall == nil {
			r.Message.ToolCall = &ToolCall{}
		}
		r.Message.ToolCall.Name += chunk
	case FieldToolCallArguments:
		if r.Message.ToolCall == nil {
			r.Message.ToolCall = &ToolCall{}
		}
		r.Message.ToolCall.Arguments += chunk
	}

	// Queue message to clients
	return r.chat.queueMessage(map[string]interface{}{
		"type":  "add_chunk",
		"id":    r.Message.ID,
		"field": field,
		"chunk": chunk,
	})
}

// End finalizes the reply
func (r *Reply) End() error {
	if err := r.chat.queueMessage(map[string]interface{}{
		"type": "end_message",
		"id":   r.Message.ID,
	}); err != nil {
		return err
	}

	r.chat.NewMessages = append(r.chat.NewMessages, r.Message)
	r.chat.State.Messages = append(r.chat.State.Messages, r.Message)
	return nil
}

// Publisher defines the function type for publishing messages
type Publisher func(map[string]interface{}) error

// Chat represents a chat session
type Chat struct {
	State       *ChatState
	NewMessages []*Message
	publisher   Publisher
}

// NewChat creates a new chat
func NewChat(state *ChatState, publisher Publisher) *Chat {
	if state == nil {
		state = &ChatState{
			ID:       generateChatID(),
			Messages: make([]*Message, 0),
		}
	}

	return &Chat{
		State:       state,
		NewMessages: make([]*Message, 0),
		publisher:   publisher,
	}
}

// Reply creates a new reply for the chat
func (c *Chat) Reply(role MessageRole, name string) (*Reply, error) {
	reply := NewReply(c, role, name)
	
	// Queue begin message
	if err := c.queueMessage(map[string]interface{}{
		"type": "begin_message",
		"id":   reply.Message.ID,
		"role": reply.Message.Role,
		"name": reply.Message.Name,
	}); err != nil {
		return nil, err
	}

	return reply, nil
}

// queueMessage queues a message for publishing
func (c *Chat) queueMessage(message map[string]interface{}) error {
	if c.publisher != nil {
		return c.publisher(message)
	}
	return nil
}

// Assistant represents an assistant
type Assistant struct {
	Name string `json:"name"`
}

// ChatSummary represents a chat summary for listing
type ChatSummary struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	LastUpdated time.Time `json:"last_updated"`
}

// SendMessageRequest represents a request to send a message
type SendMessageRequest struct {
	ID        string  `json:"id"`
	Content   string  `json:"content"`
	Assistant *string `json:"assistant,omitempty"`
}

// EditMessageRequest represents a request to edit a message
type EditMessageRequest struct {
	Content string `json:"content"`
}

// Helper functions for ID generation
func generateMessageID() string {
	return uuid.New().String()
}

func generateChatID() string {
	return uuid.New().String()
}