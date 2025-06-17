package repository

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/cenkalti/akson/internal/database"
	"github.com/cenkalti/akson/internal/models"
)

// PostgresRepository implements Repository using PostgreSQL
type PostgresRepository struct {
	db      *pgxpool.Pool
	queries *database.Queries
}

// NewPostgresRepository creates a new PostgreSQL repository
func NewPostgresRepository(db *pgxpool.Pool) *PostgresRepository {
	return &PostgresRepository{
		db:      db,
		queries: database.New(db),
	}
}

// CreateChat creates a new chat
func (r *PostgresRepository) CreateChat(ctx context.Context, id, assistant string) (*models.ChatState, error) {
	chatUUID, err := uuid.Parse(id)
	if err != nil {
		return nil, fmt.Errorf("invalid chat ID: %w", err)
	}

	params := database.CreateChatParams{
		ID:        pgtype.UUID{Bytes: chatUUID, Valid: true},
		Title:     pgtype.Text{Valid: false}, // NULL initially
		Assistant: pgtype.Text{String: assistant, Valid: true},
	}

	chat, err := r.queries.CreateChat(ctx, params)
	if err != nil {
		return nil, fmt.Errorf("failed to create chat: %w", err)
	}

	return r.dbChatToModel(chat, []*models.Message{})
}

// GetChat retrieves a chat with all its messages
func (r *PostgresRepository) GetChat(ctx context.Context, id string) (*models.ChatState, error) {
	chatUUID, err := uuid.Parse(id)
	if err != nil {
		return nil, fmt.Errorf("invalid chat ID: %w", err)
	}

	chat, err := r.queries.GetChat(ctx, pgtype.UUID{Bytes: chatUUID, Valid: true})
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("chat not found")
		}
		return nil, fmt.Errorf("failed to get chat: %w", err)
	}

	messages, err := r.queries.GetMessagesByChatID(ctx, pgtype.UUID{Bytes: chatUUID, Valid: true})
	if err != nil {
		return nil, fmt.Errorf("failed to get messages: %w", err)
	}

	modelMessages := make([]*models.Message, len(messages))
	for i, msg := range messages {
		modelMessages[i] = r.dbMessageToModel(msg)
	}

	return r.dbChatToModel(chat, modelMessages)
}

// GetChats retrieves all chat summaries
func (r *PostgresRepository) GetChats(ctx context.Context) ([]ChatSummary, error) {
	summaries, err := r.queries.GetChatSummaries(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get chat summaries: %w", err)
	}

	result := make([]ChatSummary, len(summaries))
	for i, summary := range summaries {
		result[i] = ChatSummary{
			ID:          uuid.UUID(summary.ID.Bytes).String(),
			Title:       summary.Title,
			LastUpdated: summary.LastUpdated.Time,
		}
	}

	return result, nil
}

// UpdateChatAssistant updates the assistant for a chat
func (r *PostgresRepository) UpdateChatAssistant(ctx context.Context, id, assistant string) error {
	chatUUID, err := uuid.Parse(id)
	if err != nil {
		return fmt.Errorf("invalid chat ID: %w", err)
	}

	params := database.UpdateChatAssistantParams{
		ID:        pgtype.UUID{Bytes: chatUUID, Valid: true},
		Assistant: pgtype.Text{String: assistant, Valid: true},
	}

	_, err = r.queries.UpdateChatAssistant(ctx, params)
	if err != nil {
		return fmt.Errorf("failed to update chat assistant: %w", err)
	}

	return nil
}

// DeleteChat deletes a chat and all its messages
func (r *PostgresRepository) DeleteChat(ctx context.Context, id string) error {
	chatUUID, err := uuid.Parse(id)
	if err != nil {
		return fmt.Errorf("invalid chat ID: %w", err)
	}

	err = r.queries.DeleteChat(ctx, pgtype.UUID{Bytes: chatUUID, Valid: true})
	if err != nil {
		return fmt.Errorf("failed to delete chat: %w", err)
	}

	return nil
}

// CreateMessage creates a new message
func (r *PostgresRepository) CreateMessage(ctx context.Context, chatID string, message *models.Message) error {
	chatUUID, err := uuid.Parse(chatID)
	if err != nil {
		return fmt.Errorf("invalid chat ID: %w", err)
	}

	messageUUID, err := uuid.Parse(message.ID)
	if err != nil {
		return fmt.Errorf("invalid message ID: %w", err)
	}

	params := database.CreateMessageParams{
		ID:     pgtype.UUID{Bytes: messageUUID, Valid: true},
		ChatID: pgtype.UUID{Bytes: chatUUID, Valid: true},
		Role:   string(message.Role),
		Name:   pgtype.Text{String: stringPtrToString(message.Name), Valid: message.Name != nil},
		Content: pgtype.Text{String: message.Content, Valid: message.Content != ""},
	}

	if message.ToolCall != nil {
		params.ToolCallID = pgtype.Text{String: message.ToolCall.ID, Valid: true}
		params.ToolCallName = pgtype.Text{String: message.ToolCall.Name, Valid: true}
		params.ToolCallArguments = pgtype.Text{String: message.ToolCall.Arguments, Valid: true}
	}

	if message.ToolCallID != nil {
		params.ToolCallID = pgtype.Text{String: *message.ToolCallID, Valid: true}
	}

	_, err = r.queries.CreateMessage(ctx, params)
	if err != nil {
		return fmt.Errorf("failed to create message: %w", err)
	}

	return nil
}

// GetMessages retrieves all messages for a chat
func (r *PostgresRepository) GetMessages(ctx context.Context, chatID string) ([]*models.Message, error) {
	chatUUID, err := uuid.Parse(chatID)
	if err != nil {
		return nil, fmt.Errorf("invalid chat ID: %w", err)
	}

	messages, err := r.queries.GetMessagesByChatID(ctx, pgtype.UUID{Bytes: chatUUID, Valid: true})
	if err != nil {
		return nil, fmt.Errorf("failed to get messages: %w", err)
	}

	result := make([]*models.Message, len(messages))
	for i, msg := range messages {
		result[i] = r.dbMessageToModel(msg)
	}

	return result, nil
}

// UpdateMessage updates a message's content
func (r *PostgresRepository) UpdateMessage(ctx context.Context, messageID, content string) error {
	msgUUID, err := uuid.Parse(messageID)
	if err != nil {
		return fmt.Errorf("invalid message ID: %w", err)
	}

	params := database.UpdateMessageParams{
		ID:      pgtype.UUID{Bytes: msgUUID, Valid: true},
		Content: pgtype.Text{String: content, Valid: true},
	}

	_, err = r.queries.UpdateMessage(ctx, params)
	if err != nil {
		return fmt.Errorf("failed to update message: %w", err)
	}

	return nil
}

// DeleteMessage deletes a message
func (r *PostgresRepository) DeleteMessage(ctx context.Context, messageID string) error {
	msgUUID, err := uuid.Parse(messageID)
	if err != nil {
		return fmt.Errorf("invalid message ID: %w", err)
	}

	err = r.queries.DeleteMessage(ctx, pgtype.UUID{Bytes: msgUUID, Valid: true})
	if err != nil {
		return fmt.Errorf("failed to delete message: %w", err)
	}

	return nil
}

// ClearMessages deletes all messages for a chat
func (r *PostgresRepository) ClearMessages(ctx context.Context, chatID string) error {
	chatUUID, err := uuid.Parse(chatID)
	if err != nil {
		return fmt.Errorf("invalid chat ID: %w", err)
	}

	err = r.queries.DeleteMessagesByChatID(ctx, pgtype.UUID{Bytes: chatUUID, Valid: true})
	if err != nil {
		return fmt.Errorf("failed to clear messages: %w", err)
	}

	return nil
}

// Close closes the database connection
func (r *PostgresRepository) Close() error {
	r.db.Close()
	return nil
}

// Helper functions

func (r *PostgresRepository) dbChatToModel(chat database.Chat, messages []*models.Message) (*models.ChatState, error) {
	var title *string
	if chat.Title.Valid {
		title = &chat.Title.String
	}

	var assistant *string
	if chat.Assistant.Valid {
		assistant = &chat.Assistant.String
	}

	return &models.ChatState{
		ID:        uuid.UUID(chat.ID.Bytes).String(),
		Messages:  messages,
		Assistant: assistant,
		Title:     title,
	}, nil
}

func (r *PostgresRepository) dbMessageToModel(msg database.Message) *models.Message {
	result := &models.Message{
		ID:      uuid.UUID(msg.ID.Bytes).String(),
		Role:    models.MessageRole(msg.Role),
		Content: msg.Content.String,
	}

	if msg.Name.Valid {
		result.Name = &msg.Name.String
	}

	// Handle tool calls
	if msg.ToolCallName.Valid || msg.ToolCallArguments.Valid {
		result.ToolCall = &models.ToolCall{
			ID:        msg.ToolCallID.String,
			Name:      msg.ToolCallName.String,
			Arguments: msg.ToolCallArguments.String,
		}
	}

	if msg.ToolCallID.Valid && result.ToolCall == nil {
		result.ToolCallID = &msg.ToolCallID.String
	}

	return result
}

func stringPtrToString(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}