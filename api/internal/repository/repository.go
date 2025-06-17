package repository

import (
	"context"
	"time"

	"github.com/cenkalti/akson/internal/models"
)

// ChatSummary represents a chat summary for listing
type ChatSummary struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	LastUpdated time.Time `json:"last_updated"`
}

// Repository defines the interface for chat and message storage
type Repository interface {
	// Chat operations
	CreateChat(ctx context.Context, id, assistant string) (*models.ChatState, error)
	GetChat(ctx context.Context, id string) (*models.ChatState, error)
	GetChats(ctx context.Context) ([]ChatSummary, error)
	UpdateChatAssistant(ctx context.Context, id, assistant string) error
	DeleteChat(ctx context.Context, id string) error

	// Message operations
	CreateMessage(ctx context.Context, chatID string, message *models.Message) error
	GetMessages(ctx context.Context, chatID string) ([]*models.Message, error)
	UpdateMessage(ctx context.Context, messageID, content string) error
	DeleteMessage(ctx context.Context, messageID string) error
	ClearMessages(ctx context.Context, chatID string) error

	// Utility operations
	Close() error
}