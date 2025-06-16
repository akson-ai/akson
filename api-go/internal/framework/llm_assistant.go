package framework

import (
	"fmt"
	"log/slog"
	"os"

	"github.com/cenkalti/akson/internal/models"
	"github.com/cenkalti/akson/pkg/akson"
)

// LLMAssistant implements an assistant using Anthropic's Claude API
type LLMAssistant struct {
	akson.BaseAssistant
	Model        string
	SystemPrompt string
	MaxTokens    int
	Temperature  float64
	client       *AnthropicClient
}

// NewLLMAssistant creates a new LLM assistant
func NewLLMAssistant(name, model, systemPrompt string) *LLMAssistant {
	if model == "" {
		model = getDefaultModel()
	}

	return &LLMAssistant{
		BaseAssistant: akson.BaseAssistant{
			Name:        name,
			Description: fmt.Sprintf("%s powered by %s", name, model),
		},
		Model:        model,
		SystemPrompt: systemPrompt,
		MaxTokens:    4096,
		Temperature:  0.7,
		client:       NewAnthropicClient(),
	}
}

// Run implements the AssistantInterface
func (a *LLMAssistant) Run(chat *models.Chat) error {
	// Convert messages to Anthropic format
	messages := make([]AnthropicMessage, 0)
	
	for _, msg := range chat.State.Messages {
		// Skip system messages and tool calls for now
		if msg.Role == models.RoleUser || msg.Role == models.RoleAssistant {
			anthropicRole := string(msg.Role)
			messages = append(messages, AnthropicMessage{
				Role:    anthropicRole,
				Content: msg.Content,
			})
		}
	}

	// Create the request
	req := AnthropicRequest{
		Model:       a.Model,
		MaxTokens:   a.MaxTokens,
		Messages:    messages,
		System:      a.SystemPrompt,
		Temperature: a.Temperature,
	}

	// Create reply for streaming
	reply, err := chat.Reply(models.RoleAssistant, a.Name)
	if err != nil {
		return fmt.Errorf("failed to create reply: %w", err)
	}

	// Stream the response
	err = a.client.CreateMessageStream(req, func(chunk string) error {
		return reply.AddChunk(chunk, models.FieldContent)
	})

	if err != nil {
		slog.Error("Anthropic API error", "error", err)
		// Send error chunk
		errorMsg := fmt.Sprintf("Sorry, I encountered an error: %v", err)
		if chunkErr := reply.AddChunk(errorMsg, models.FieldContent); chunkErr != nil {
			return fmt.Errorf("failed to add error chunk: %w", chunkErr)
		}
	}

	// End the reply
	if endErr := reply.End(); endErr != nil {
		return fmt.Errorf("failed to end reply: %w", endErr)
	}

	return nil
}

// getDefaultModel returns the default model from environment or fallback
func getDefaultModel() string {
	if model := os.Getenv("DEFAULT_MODEL"); model != "" {
		return model
	}
	return "claude-3-5-sonnet-20241022" // Default Claude model
}