package main

import (
	"context"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/cenkalti/akson/internal/database"
	"github.com/cenkalti/akson/internal/handlers"
	"github.com/cenkalti/akson/internal/registry"
	"github.com/cenkalti/akson/internal/repository"
	"github.com/cenkalti/akson/internal/streaming"
)

func main() {
	// Setup structured logging
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	ctx := context.Background()

	// Initialize database
	dbConfig := database.LoadConfig()
	
	// Run migrations
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

	// Initialize components
	pubsub := streaming.NewPubSub()
	assistantRegistry := registry.NewRegistry()
	
	// Initialize HTTP handlers
	handler := handlers.NewHandler(pubsub, assistantRegistry, repo)

	// Setup HTTP server with custom mux
	mux := http.NewServeMux()
	
	// Add CORS middleware
	corsHandler := corsMiddleware(mux)
	
	// Register routes
	registerRoutes(mux, handler)
	
	// HTTP server configuration
	srv := &http.Server{
		Addr:         ":8000",
		Handler:      corsHandler,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		slog.Info("Starting server", "addr", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed to start: %v", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	
	slog.Info("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	slog.Info("Server stopped")
}

// registerRoutes sets up all HTTP routes
func registerRoutes(mux *http.ServeMux, h *handlers.Handler) {
	// Health check
	mux.HandleFunc("GET /health", h.HealthCheck)
	
	// Assistants
	mux.HandleFunc("GET /assistants", h.GetAssistants)
	
	// Chats
	mux.HandleFunc("GET /chats", h.GetChats)
	mux.HandleFunc("GET /chats/{id}", h.GetChatState)
	mux.HandleFunc("PUT /chats/{id}/assistant", h.SetAssistant)
	mux.HandleFunc("POST /chats/{id}/messages", h.SendMessage)
	mux.HandleFunc("PUT /chats/{id}/messages/{messageId}", h.EditMessage)
	mux.HandleFunc("DELETE /chats/{id}/messages/{messageId}", h.DeleteMessage)
	mux.HandleFunc("POST /chats/{id}/messages/{messageId}/retry", h.RetryMessage)
	mux.HandleFunc("POST /chats/{id}/messages/{messageId}/fork", h.ForkChat)
	mux.HandleFunc("DELETE /chats/{id}", h.DeleteChat)
	mux.HandleFunc("GET /chats/{id}/events", h.GetEvents)
}

// corsMiddleware adds CORS headers to all responses
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Get allowed origins from environment
		allowedOrigins := os.Getenv("ALLOW_ORIGINS")
		if allowedOrigins == "" {
			allowedOrigins = "*"
		}
		
		w.Header().Set("Access-Control-Allow-Origin", allowedOrigins)
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		
		// Handle preflight requests
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		
		next.ServeHTTP(w, r)
	})
}