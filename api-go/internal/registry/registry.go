package registry

import (
	"fmt"
	"log/slog"
	"sort"
	"strings"

	"github.com/cenkalti/akson/internal/framework"
	"github.com/cenkalti/akson/pkg/akson"
)

// Registry manages available assistants
type Registry struct {
	assistants map[string]akson.AssistantInterface
}

// NewRegistry creates a new assistant registry
func NewRegistry() *Registry {
	registry := &Registry{
		assistants: make(map[string]akson.AssistantInterface),
	}
	
	// Load built-in assistants
	registry.loadBuiltinAssistants()
	
	return registry
}

// Register adds an assistant to the registry
func (r *Registry) Register(assistant akson.AssistantInterface) error {
	name := strings.ToLower(assistant.GetName())
	
	if _, exists := r.assistants[name]; exists {
		return fmt.Errorf("assistant with name %q already exists", assistant.GetName())
	}
	
	r.assistants[name] = assistant
	slog.Info("Registered assistant", "name", assistant.GetName())
	return nil
}

// GetAssistant retrieves an assistant by name (case-insensitive, supports prefix matching)
func (r *Registry) GetAssistant(name string) (akson.AssistantInterface, error) {
	name = strings.ToLower(name)
	
	// Exact match first
	if assistant, exists := r.assistants[name]; exists {
		return assistant, nil
	}
	
	// Prefix matching
	var matches []akson.AssistantInterface
	for assistantName, assistant := range r.assistants {
		if strings.HasPrefix(assistantName, name) {
			matches = append(matches, assistant)
		}
	}
	
	if len(matches) == 1 {
		return matches[0], nil
	}
	
	if len(matches) > 1 {
		names := make([]string, len(matches))
		for i, assistant := range matches {
			names[i] = assistant.GetName()
		}
		return nil, fmt.Errorf("ambiguous assistant name %q, matches: %s", name, strings.Join(names, ", "))
	}
	
	return nil, fmt.Errorf("unknown assistant: %s", name)
}

// GetAllAssistants returns all registered assistants
func (r *Registry) GetAllAssistants() []akson.AssistantInterface {
	assistants := make([]akson.AssistantInterface, 0, len(r.assistants))
	
	// Create a sorted list by name
	names := make([]string, 0, len(r.assistants))
	for name := range r.assistants {
		names = append(names, name)
	}
	sort.Strings(names)
	
	for _, name := range names {
		assistants = append(assistants, r.assistants[name])
	}
	
	return assistants
}

// GetDefaultAssistant returns the default assistant
func (r *Registry) GetDefaultAssistant() akson.AssistantInterface {
	// Try to get the configured default
	if defaultName := getDefaultAssistantName(); defaultName != "" {
		if assistant, err := r.GetAssistant(defaultName); err == nil {
			return assistant
		}
	}
	
	// Fall back to first available assistant
	assistants := r.GetAllAssistants()
	if len(assistants) > 0 {
		return assistants[0]
	}
	
	// This should not happen if we have built-in assistants
	panic("no assistants available")
}

// loadBuiltinAssistants loads the built-in assistants
func (r *Registry) loadBuiltinAssistants() {
	// Register Claude assistant
	claude := framework.NewLLMAssistant(
		"Claude",
		"claude-3-5-sonnet-20241022",
		"You are Claude, a helpful AI assistant created by Anthropic.",
	)
	
	// Register a basic ChatGPT placeholder (would need OpenAI implementation)
	chatgpt := &BasicAssistant{
		BaseAssistant: akson.BaseAssistant{
			Name:        "ChatGPT", 
			Description: "OpenAI ChatGPT Assistant (placeholder)",
		},
	}
	
	r.Register(claude)
	r.Register(chatgpt)
}

// getDefaultAssistantName returns the default assistant name from environment
func getDefaultAssistantName() string {
	// This would read from environment variable
	// For now, default to Claude
	return "Claude"
}

// BasicAssistant is a simple assistant implementation for testing
type BasicAssistant struct {
	akson.BaseAssistant
}

// Run implements the AssistantInterface
func (a *BasicAssistant) Run(chat *akson.Chat) error {
	reply, err := chat.Reply(akson.RoleAssistant, a.Name)
	if err != nil {
		return err
	}
	
	// Simple echo response for now
	err = reply.AddChunk("I'm a basic assistant. Full implementation coming soon!", akson.FieldContent)
	if err != nil {
		return err
	}
	
	return reply.End()
}