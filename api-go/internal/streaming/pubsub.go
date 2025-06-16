package streaming

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"sync"
)

// Subscriber represents a client subscribed to a chat
type Subscriber struct {
	ID      string
	Channel chan []byte
	Done    chan struct{}
}

// NewSubscriber creates a new subscriber
func NewSubscriber(id string) *Subscriber {
	return &Subscriber{
		ID:      id,
		Channel: make(chan []byte, 100), // Buffered channel
		Done:    make(chan struct{}),
	}
}

// Close closes the subscriber
func (s *Subscriber) Close() {
	close(s.Done)
	close(s.Channel)
}

// PubSub manages real-time message broadcasting
type PubSub struct {
	subscribers map[string][]*Subscriber
	mu          sync.RWMutex
}

// NewPubSub creates a new PubSub instance
func NewPubSub() *PubSub {
	return &PubSub{
		subscribers: make(map[string][]*Subscriber),
	}
}

// Subscribe adds a subscriber to a chat channel
func (ps *PubSub) Subscribe(chatID, subscriberID string) *Subscriber {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	subscriber := NewSubscriber(subscriberID)
	ps.subscribers[chatID] = append(ps.subscribers[chatID], subscriber)
	
	slog.Info("Client subscribed", "chatID", chatID, "subscriberID", subscriberID)
	return subscriber
}

// Unsubscribe removes a subscriber from a chat channel
func (ps *PubSub) Unsubscribe(chatID, subscriberID string) {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	subscribers := ps.subscribers[chatID]
	for i, sub := range subscribers {
		if sub.ID == subscriberID {
			sub.Close()
			// Remove from slice
			ps.subscribers[chatID] = append(subscribers[:i], subscribers[i+1:]...)
			break
		}
	}
	
	// Clean up empty chat channels
	if len(ps.subscribers[chatID]) == 0 {
		delete(ps.subscribers, chatID)
	}
	
	slog.Info("Client unsubscribed", "chatID", chatID, "subscriberID", subscriberID)
}

// Publish sends a message to all subscribers of a chat
func (ps *PubSub) Publish(chatID string, message map[string]interface{}) error {
	ps.mu.RLock()
	subscribers := ps.subscribers[chatID]
	ps.mu.RUnlock()

	if len(subscribers) == 0 {
		return nil // No subscribers
	}

	// Marshal message to JSON
	data, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("failed to marshal message: %w", err)
	}

	// Send to all subscribers
	for _, sub := range subscribers {
		select {
		case sub.Channel <- data:
			// Message sent
		case <-sub.Done:
			// Subscriber is closed
		default:
			// Channel full, skip (could log warning)
			slog.Warn("Subscriber channel full, dropping message", "chatID", chatID, "subscriberID", sub.ID)
		}
	}

	return nil
}

// GetSubscriberCount returns the number of subscribers for a chat
func (ps *PubSub) GetSubscriberCount(chatID string) int {
	ps.mu.RLock()
	defer ps.mu.RUnlock()
	return len(ps.subscribers[chatID])
}