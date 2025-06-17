package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"

	"github.com/google/uuid"

	"github.com/cenkalti/akson/internal/models"
	"github.com/cenkalti/akson/internal/registry"
	"github.com/cenkalti/akson/internal/repository"
	"github.com/cenkalti/akson/internal/streaming"
)

// getChatsDirectory returns the chats directory path
func getChatsDirectory() string {
	if dir := os.Getenv("CHATS_DIR"); dir != "" {
		return dir
	}
	return "chats"
}

// Handler contains the HTTP handlers
type Handler struct {
	pubsub   *streaming.PubSub
	registry *registry.Registry
	repo     repository.Repository
}

// NewHandler creates a new handler
func NewHandler(pubsub *streaming.PubSub, registry *registry.Registry, repo repository.Repository) *Handler {
	return &Handler{
		pubsub:   pubsub,
		registry: registry,
		repo:     repo,
	}
}

// HealthCheck handles health check requests
func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	
	// Check database health by trying to get chats count
	_, err := h.repo.GetChats(ctx)
	if err != nil {
		slog.Error("Database health check failed", "error", err)
		response := map[string]string{
			"status": "unhealthy",
			"error":  "database connection failed",
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(response)
		return
	}

	response := map[string]string{"status": "healthy"}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// GetAssistants returns all available assistants
func (h *Handler) GetAssistants(w http.ResponseWriter, r *http.Request) {
	assistants := h.registry.GetAllAssistants()
	
	response := make([]models.Assistant, len(assistants))
	for i, assistant := range assistants {
		response[i] = models.Assistant{
			Name: assistant.GetName(),
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// GetChats returns all chat sessions
func (h *Handler) GetChats(w http.ResponseWriter, r *http.Request) {
	chatSummaries, err := h.repo.GetChats(r.Context())
	if err != nil {
		slog.Error("Failed to get chats", "error", err)
		http.Error(w, "Failed to get chats", http.StatusInternalServerError)
		return
	}

	// Convert to models.ChatSummary format
	modelSummaries := make([]models.ChatSummary, len(chatSummaries))
	for i, summary := range chatSummaries {
		modelSummaries[i] = models.ChatSummary{
			ID:          summary.ID,
			Title:       summary.Title,
			LastUpdated: summary.LastUpdated,
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(modelSummaries)
}

// GetChatState returns a specific chat state
func (h *Handler) GetChatState(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	if chatID == "" {
		http.Error(w, "Chat ID is required", http.StatusBadRequest)
		return
	}
	
	state, err := h.repo.GetChat(r.Context(), chatID)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			// Create new chat if it doesn't exist
			defaultAssistant := h.registry.GetDefaultAssistant()
			state, err = h.repo.CreateChat(r.Context(), chatID, defaultAssistant.GetName())
			if err != nil {
				slog.Error("Failed to create new chat", "chatID", chatID, "error", err)
				http.Error(w, "Failed to create chat", http.StatusInternalServerError)
				return
			}
		} else {
			slog.Error("Failed to get chat state", "chatID", chatID, "error", err)
			http.Error(w, "Failed to load chat", http.StatusInternalServerError)
			return
		}
	}
	
	w.Header().Set("Content-Type", "application/json")  
	json.NewEncoder(w).Encode(state)
}

// SetAssistant updates the assistant for a chat
func (h *Handler) SetAssistant(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	if chatID == "" {
		http.Error(w, "Chat ID is required", http.StatusBadRequest)
		return
	}
	
	var requestBody map[string]string
	if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	
	assistantName, ok := requestBody["assistant"]
	if !ok {
		http.Error(w, "Assistant name is required", http.StatusBadRequest)
		return
	}
	
	err := h.repo.UpdateChatAssistant(r.Context(), chatID, assistantName)
	if err != nil {
		slog.Error("Failed to update chat assistant", "chatID", chatID, "error", err)
		http.Error(w, "Failed to update chat assistant", http.StatusInternalServerError)
		return
	}
	
	w.WriteHeader(http.StatusOK)
}

// SendMessage handles sending a message to a chat
func (h *Handler) SendMessage(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	if chatID == "" {
		http.Error(w, "Chat ID is required", http.StatusBadRequest)
		return
	}
	
	var req models.SendMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	
	// Handle commands
	if strings.HasPrefix(req.Content, "/") {
		messages, err := h.handleCommand(r.Context(), chatID, req.Content)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(messages)
		return
	}
	
	// Get chat and assistant
	chat, err := h.getChat(r.Context(), chatID)
	if err != nil {
		slog.Error("Failed to get chat for message send", "chatID", chatID, "error", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	
	// Determine which assistant to use
	assistantName := ""
	if req.Assistant != nil {
		assistantName = *req.Assistant
	} else if chat.State.Assistant != nil {
		assistantName = *chat.State.Assistant
	} else if strings.HasPrefix(req.Content, "@") {
		parts := strings.Fields(req.Content)
		if len(parts) > 0 {
			assistantName = strings.TrimPrefix(parts[0], "@")
		}
	}
	
	if assistantName == "" {
		assistantName = h.registry.GetDefaultAssistant().GetName()
	}
	
	assistant, err := h.registry.GetAssistant(assistantName)
	if err != nil {
		http.Error(w, fmt.Sprintf("Unknown assistant: %s", assistantName), http.StatusBadRequest)
		return
	}
	
	// Create user message
	userMessage := models.NewMessage(models.RoleUser, req.Content)
	userMessage.ID = req.ID
	
	// Save user message to repository
	if err := h.repo.CreateMessage(r.Context(), chatID, userMessage); err != nil {
		slog.Error("Failed to save user message", "error", err)
		http.Error(w, "Failed to save message", http.StatusInternalServerError)
		return
	}
	
	// Add to chat state for assistant processing
	chat.State.Messages = append(chat.State.Messages, userMessage)
	
	// Run assistant
	if err := assistant.Run(chat); err != nil {
		slog.Error("Assistant run failed", "error", err)
		// Send error message to chat
		h.sendErrorMessage(chat, err)
	}
	
	// Save all new messages to repository
	for _, message := range chat.NewMessages {
		if err := h.repo.CreateMessage(r.Context(), chatID, message); err != nil {
			slog.Error("Failed to save assistant message", "messageID", message.ID, "error", err)
		}
	}
	
	// Return new messages
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(chat.NewMessages)
}

// EditMessage edits a message
func (h *Handler) EditMessage(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	messageID := r.PathValue("messageId")
	
	var req models.EditMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}
	
	err := h.repo.UpdateMessage(r.Context(), messageID, req.Content)
	if err != nil {
		slog.Error("Failed to update message", "chatID", chatID, "messageID", messageID, "error", err)
		http.Error(w, "Failed to update message", http.StatusInternalServerError)
		return
	}
	
	w.WriteHeader(http.StatusOK)
}

// DeleteMessage deletes a message
func (h *Handler) DeleteMessage(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	messageID := r.PathValue("messageId")
	
	err := h.repo.DeleteMessage(r.Context(), messageID)
	if err != nil {
		slog.Error("Failed to delete message", "chatID", chatID, "messageID", messageID, "error", err)
		http.Error(w, "Failed to delete message", http.StatusInternalServerError)
		return
	}
	
	w.WriteHeader(http.StatusOK)
}

// RetryMessage retries from a specific message
func (h *Handler) RetryMessage(w http.ResponseWriter, r *http.Request) {
	// TODO: Implement retry logic
	http.Error(w, "Not implemented yet", http.StatusNotImplemented)
}

// ForkChat creates a new chat forked from a message
func (h *Handler) ForkChat(w http.ResponseWriter, r *http.Request) {
	// TODO: Implement fork logic  
	http.Error(w, "Not implemented yet", http.StatusNotImplemented)
}

// DeleteChat deletes a chat
func (h *Handler) DeleteChat(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	if chatID == "" {
		http.Error(w, "Chat ID is required", http.StatusBadRequest)
		return
	}
	
	err := h.repo.DeleteChat(r.Context(), chatID)
	if err != nil {
		slog.Error("Failed to delete chat", "chatID", chatID, "error", err)
		http.Error(w, "Failed to delete chat", http.StatusInternalServerError)
		return
	}
	
	w.WriteHeader(http.StatusOK)
}

// GetEvents handles Server-Sent Events for a chat
func (h *Handler) GetEvents(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	if chatID == "" {
		http.Error(w, "Chat ID is required", http.StatusBadRequest)
		return
	}
	
	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	// Create subscriber
	subscriberID := uuid.New().String()
	subscriber := h.pubsub.Subscribe(chatID, subscriberID)
	defer h.pubsub.Unsubscribe(chatID, subscriberID)
	
	// Get flusher for real-time streaming
	flusher, ok := w.(http.Flusher)
	if !ok {
		slog.Error("HTTP response writer does not support streaming", "chatID", chatID)
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}
	
	// Send events
	for {
		select {
		case data := <-subscriber.Channel:
			fmt.Fprintf(w, "data: %s\n\n", data)
			flusher.Flush()
		case <-subscriber.Done:
			return
		case <-r.Context().Done():
			return
		}
	}
}

// Helper methods

func (h *Handler) getChatState(ctx context.Context, chatID string) (*models.ChatState, error) {
	state, err := h.repo.GetChat(ctx, chatID)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			// Create new chat
			defaultAssistant := h.registry.GetDefaultAssistant()
			return h.repo.CreateChat(ctx, chatID, defaultAssistant.GetName())
		}
		return nil, fmt.Errorf("failed to load chat: %w", err)
	}
	return state, nil
}

func (h *Handler) getChat(ctx context.Context, chatID string) (*models.Chat, error) {
	state, err := h.getChatState(ctx, chatID)
	if err != nil {
		return nil, err
	}
	
	// Create publisher function
	publisher := func(message map[string]interface{}) error {
		return h.pubsub.Publish(chatID, message)
	}
	
	return models.NewChat(state, publisher), nil
}

func (h *Handler) handleCommand(ctx context.Context, chatID, content string) ([]*models.Message, error) {
	parts := strings.Fields(content)
	if len(parts) == 0 {
		return nil, fmt.Errorf("empty command")
	}
	
	command := parts[0]
	args := parts[1:]
	
	switch command {
	case "/clear":
		err := h.repo.ClearMessages(ctx, chatID)
		if err != nil {
			return nil, fmt.Errorf("failed to clear messages: %w", err)
		}
		
		// Send clear message
		h.pubsub.Publish(chatID, map[string]interface{}{"type": "clear"})
		
		return []*models.Message{
			models.NewMessage(models.RoleAssistant, "Chat cleared"),
		}, nil
		
	case "/assistant":
		if len(args) != 1 {
			return nil, fmt.Errorf("usage: /assistant <name>")
		}
		
		assistant, err := h.registry.GetAssistant(args[0])
		if err != nil {
			return nil, err
		}
		
		assistantName := assistant.GetName()
		err = h.repo.UpdateChatAssistant(ctx, chatID, assistantName)
		if err != nil {
			return nil, fmt.Errorf("failed to update chat assistant: %w", err)
		}
		
		// Send update message
		h.pubsub.Publish(chatID, map[string]interface{}{
			"type":      "update_assistant",
			"assistant": assistantName,
		})
		
		return []*models.Message{
			models.NewMessage(models.RoleAssistant, fmt.Sprintf("Assistant set to %s", assistantName)),
		}, nil
		
	default:
		return nil, fmt.Errorf("unknown command: %s", command)
	}
}

func (h *Handler) sendErrorMessage(chat *models.Chat, err error) {
	reply, replyErr := chat.Reply(models.RoleAssistant, "Error")
	if replyErr != nil {
		slog.Error("Failed to create error reply", "error", replyErr)
		return
	}
	
	content := fmt.Sprintf("Error: %v", err)
	if addErr := reply.AddChunk(content, models.FieldContent); addErr != nil {
		slog.Error("Failed to add error chunk", "error", addErr)
		return
	}
	
	if endErr := reply.End(); endErr != nil {
		slog.Error("Failed to end error reply", "error", endErr)
	}
}