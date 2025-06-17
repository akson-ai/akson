package main

import (
	"context"
	"log"
	"log/slog"
	"os"
	"strings"

	"github.com/cenkalti/akson/internal/database"
	"github.com/cenkalti/akson/internal/models"
	"github.com/cenkalti/akson/internal/repository"
)

func main() {
	// Setup structured logging
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	ctx := context.Background()

	// Initialize database
	dbConfig := database.LoadConfig()
	
	// Run migrations first
	if err := database.RunMigrations(dbConfig, "migrations"); err != nil {
		log.Fatalf("Failed to run migrations: %v", err)
	}

	// Connect to database
	db, err := database.Connect(ctx, dbConfig)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	// Initialize repository
	repo := repository.NewPostgresRepository(db)
	defer repo.Close()

	// Get chats directory
	chatsDir := getChatsDirectory()
	if _, err := os.Stat(chatsDir); os.IsNotExist(err) {
		slog.Info("No chats directory found, skipping migration", "dir", chatsDir)
		return
	}

	// Read all JSON files
	entries, err := os.ReadDir(chatsDir)
	if err != nil {
		log.Fatalf("Failed to read chats directory: %v", err)
	}

	migratedCount := 0
	skippedCount := 0

	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".json") {
			chatID := strings.TrimSuffix(entry.Name(), ".json")
			
			slog.Info("Migrating chat", "chatID", chatID)

			// Check if chat already exists in database
			existingChat, err := repo.GetChat(ctx, chatID)
			if err == nil && existingChat != nil {
				slog.Info("Chat already exists in database, skipping", "chatID", chatID)
				skippedCount++
				continue
			}

			// Load from JSON file
			chatState, err := models.LoadFromDisk(chatID)
			if err != nil {
				slog.Error("Failed to load chat from disk", "chatID", chatID, "error", err)
				continue
			}

			// Create chat in database
			assistant := "Claude" // Default assistant if not set
			if chatState.Assistant != nil {
				assistant = *chatState.Assistant
			}

			_, err = repo.CreateChat(ctx, chatID, assistant)
			if err != nil {
				slog.Error("Failed to create chat in database", "chatID", chatID, "error", err)
				continue
			}

			// Migrate all messages
			for _, message := range chatState.Messages {
				err := repo.CreateMessage(ctx, chatID, message)
				if err != nil {
					slog.Error("Failed to create message in database", "chatID", chatID, "messageID", message.ID, "error", err)
					continue
				}
			}

			slog.Info("Successfully migrated chat", "chatID", chatID, "messageCount", len(chatState.Messages))
			migratedCount++
		}
	}

	slog.Info("Migration completed", 
		"migrated", migratedCount, 
		"skipped", skippedCount, 
		"total", migratedCount+skippedCount)
}

// getChatsDirectory returns the chats directory path
func getChatsDirectory() string {
	if dir := os.Getenv("CHATS_DIR"); dir != "" {
		return dir
	}
	return "chats"
}