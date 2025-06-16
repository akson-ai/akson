package akson

import "github.com/cenkalti/akson/internal/models"

// Re-export types from models for convenience
type Chat = models.Chat
type MessageRole = models.MessageRole
type FieldType = models.FieldType

// Constants
const (
	RoleUser      = models.RoleUser
	RoleAssistant = models.RoleAssistant
	RoleTool      = models.RoleTool
	
	FieldContent           = models.FieldContent
	FieldToolCallID        = models.FieldToolCallID
	FieldToolCallName      = models.FieldToolCallName
	FieldToolCallArguments = models.FieldToolCallArguments
	FieldToolCallIDDirect  = models.FieldToolCallIDDirect
)

// AssistantInterface defines the interface that all assistants must implement
type AssistantInterface interface {
	// Run executes the assistant with the given chat
	Run(chat *Chat) error
	
	// GetName returns the name of the assistant
	GetName() string
	
	// GetDescription returns the description of the assistant
	GetDescription() string
}

// BaseAssistant provides common functionality for assistants
type BaseAssistant struct {
	Name        string
	Description string
}

// GetName returns the assistant's name
func (a *BaseAssistant) GetName() string {
	return a.Name
}

// GetDescription returns the assistant's description  
func (a *BaseAssistant) GetDescription() string {
	return a.Description
}