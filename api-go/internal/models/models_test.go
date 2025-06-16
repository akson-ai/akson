package models

import (
	"os"
	"testing"
)

func TestChatStateBasics(t *testing.T) {
	// Test creating a new chat state
	state := CreateNew("TestAssistant")
	
	if state.ID == "" {
		t.Error("Expected chat state to have an ID")
	}
	
	if state.Assistant == nil || *state.Assistant != "TestAssistant" {
		t.Error("Expected assistant to be set to TestAssistant")
	}
	
	if len(state.Messages) != 0 {
		t.Error("Expected new chat state to have no messages")
	}
}

func TestMessageCreation(t *testing.T) {
	msg := NewMessage(RoleUser, "Hello, world!")
	
	if msg.ID == "" {
		t.Error("Expected message to have an ID")
	}
	
	if msg.Role != RoleUser {
		t.Error("Expected message role to be user")
	}
	
	if msg.Content != "Hello, world!" {
		t.Error("Expected message content to match")
	}
}

func TestChatStatePersistence(t *testing.T) {
	// Create a temporary directory for testing
	tempDir := t.TempDir()
	os.Setenv("CHATS_DIR", tempDir)
	defer os.Unsetenv("CHATS_DIR")
	
	// Create and save a chat state
	originalState := CreateNew("TestAssistant")
	originalState.Messages = append(originalState.Messages, NewMessage(RoleUser, "Test message"))
	
	err := originalState.SaveToDisk()
	if err != nil {
		t.Fatalf("Failed to save chat state: %v", err)
	}
	
	// Load the chat state back
	loadedState, err := LoadFromDisk(originalState.ID)
	if err != nil {
		t.Fatalf("Failed to load chat state: %v", err)
	}
	
	// Verify the loaded state matches
	if loadedState.ID != originalState.ID {
		t.Error("Loaded state ID doesn't match original")
	}
	
	if len(loadedState.Messages) != 1 {
		t.Error("Expected loaded state to have 1 message")
	}
	
	if loadedState.Messages[0].Content != "Test message" {
		t.Error("Loaded message content doesn't match")
	}
}