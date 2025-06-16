package handlers

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"

	"github.com/google/uuid"

	"github.com/cenkalti/akson/internal/models"
	"github.com/cenkalti/akson/internal/registry"
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
}

// NewHandler creates a new handler
func NewHandler(pubsub *streaming.PubSub, registry *registry.Registry) *Handler {
	return &Handler{
		pubsub:   pubsub,
		registry: registry,
	}
}

// HealthCheck handles health check requests
func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
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
	var chatSummaries []models.ChatSummary
	
	chatsDir := getChatsDirectory()
	entries, err := os.ReadDir(chatsDir)
	if err != nil {
		if os.IsNotExist(err) {
			// Return empty list if chats directory doesn't exist
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(chatSummaries)
			return
		}
		slog.Error("Failed to read chats directory", "error", err)
		http.Error(w, "Failed to read chats directory", http.StatusInternalServerError)
		return
	}
	
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".json") {
			chatID := strings.TrimSuffix(entry.Name(), ".json")
			
			state, err := models.LoadFromDisk(chatID)
			if err != nil {
				slog.Error("Failed to load chat", "chatID", chatID, "error", err)
				continue
			}
			
			// Get file modification time
			filePath := models.FilePath(chatID)
			info, err := os.Stat(filePath)
			if err != nil {
				slog.Error("Failed to stat chat file", "chatID", chatID, "error", err)
				continue
			}
			
			title := "Untitled Chat"
			if state.Title != nil {
				title = *state.Title
			}
			
			chatSummaries = append(chatSummaries, models.ChatSummary{
				ID:          chatID,
				Title:       title,
				LastUpdated: info.ModTime(),
			})
		}
	}
	
	// Sort by last updated, newest first
	// (Simple bubble sort for now)
	for i := 0; i < len(chatSummaries)-1; i++ {
		for j := 0; j < len(chatSummaries)-i-1; j++ {
			if chatSummaries[j].LastUpdated.Before(chatSummaries[j+1].LastUpdated) {
				chatSummaries[j], chatSummaries[j+1] = chatSummaries[j+1], chatSummaries[j]
			}
		}
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(chatSummaries)
}

// GetChatState returns a specific chat state
func (h *Handler) GetChatState(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	if chatID == "" {
		http.Error(w, "Chat ID is required", http.StatusBadRequest)
		return
	}
	
	state, err := models.LoadFromDisk(chatID)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			http.Error(w, "Chat not found", http.StatusNotFound)
			return
		}
		slog.Error("Failed to load chat", "chatID", chatID, "error", err)
		http.Error(w, "Failed to load chat", http.StatusInternalServerError)
		return
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
	
	state, err := h.getChatState(chatID)
	if err != nil {
		slog.Error("Failed to get chat state for assistant update", "chatID", chatID, "error", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	
	state.Assistant = &assistantName
	if err := state.SaveToDisk(); err != nil {
		slog.Error("Failed to save chat state after assistant update", "chatID", chatID, "error", err)
		http.Error(w, "Failed to save chat state", http.StatusInternalServerError)
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
		messages, err := h.handleCommand(chatID, req.Content)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(messages)
		return
	}
	
	// Get chat and assistant
	chat, err := h.getChat(chatID)
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
	
	chat.State.Messages = append(chat.State.Messages, userMessage)
	
	// Run assistant
	if err := assistant.Run(chat); err != nil {
		slog.Error("Assistant run failed", "error", err)
		// Send error message to chat
		h.sendErrorMessage(chat, err)
	}
	
	// Save chat state
	if err := chat.State.SaveToDisk(); err != nil {
		slog.Error("Failed to save chat state", "error", err)
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
	
	state, err := h.getChatState(chatID)
	if err != nil {
		slog.Error("Failed to get chat state for message edit", "chatID", chatID, "messageID", messageID, "error", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	
	// Find and update message
	found := false
	for _, msg := range state.Messages {
		if msg.ID == messageID {
			msg.Content = req.Content
			found = true
			break
		}
	}
	
	if !found {
		http.Error(w, "Message not found", http.StatusNotFound)
		return
	}
	
	if err := state.SaveToDisk(); err != nil {
		slog.Error("Failed to save chat state after message edit", "chatID", chatID, "messageID", messageID, "error", err)
		http.Error(w, "Failed to save chat state", http.StatusInternalServerError)
		return
	}
	
	w.WriteHeader(http.StatusOK)
}

// DeleteMessage deletes a message
func (h *Handler) DeleteMessage(w http.ResponseWriter, r *http.Request) {
	chatID := r.PathValue("id")
	messageID := r.PathValue("messageId")
	
	state, err := h.getChatState(chatID)
	if err != nil {
		slog.Error("Failed to get chat state for message delete", "chatID", chatID, "messageID", messageID, "error", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	
	// Filter out the message
	var newMessages []*models.Message
	for _, msg := range state.Messages {
		if msg.ID != messageID {
			newMessages = append(newMessages, msg)
		}
	}
	
	state.Messages = newMessages
	
	if err := state.SaveToDisk(); err != nil {
		slog.Error("Failed to save chat state after message delete", "chatID", chatID, "messageID", messageID, "error", err)
		http.Error(w, "Failed to save chat state", http.StatusInternalServerError)
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
	
	filePath := models.FilePath(chatID)
	if err := os.Remove(filePath); err != nil && !os.IsNotExist(err) {
		slog.Error("Failed to delete chat file", "chatID", chatID, "filePath", filePath, "error", err)
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

func (h *Handler) getChatState(chatID string) (*models.ChatState, error) {
	state, err := models.LoadFromDisk(chatID)
	if err != nil {
		if os.IsNotExist(err) {
			// Create new chat
			defaultAssistant := h.registry.GetDefaultAssistant()
			return models.NewChatState(chatID, defaultAssistant.GetName()), nil
		}
		return nil, fmt.Errorf("failed to load chat: %w", err)
	}
	return state, nil
}

func (h *Handler) getChat(chatID string) (*models.Chat, error) {
	state, err := h.getChatState(chatID)
	if err != nil {
		return nil, err
	}
	
	// Create publisher function
	publisher := func(message map[string]interface{}) error {
		return h.pubsub.Publish(chatID, message)
	}
	
	return models.NewChat(state, publisher), nil
}

func (h *Handler) handleCommand(chatID, content string) ([]*models.Message, error) {
	parts := strings.Fields(content)
	if len(parts) == 0 {
		return nil, fmt.Errorf("empty command")
	}
	
	command := parts[0]
	args := parts[1:]
	
	switch command {
	case "/clear":
		chat, err := h.getChat(chatID)
		if err != nil {
			return nil, err
		}
		
		chat.State.Messages = []*models.Message{}
		if err := chat.State.SaveToDisk(); err != nil {
			return nil, fmt.Errorf("failed to save chat: %w", err)
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
		
		chat, err := h.getChat(chatID)
		if err != nil {
			return nil, err
		}
		
		assistantName := assistant.GetName()
		chat.State.Assistant = &assistantName
		if err := chat.State.SaveToDisk(); err != nil {
			return nil, fmt.Errorf("failed to save chat: %w", err)
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