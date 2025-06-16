# Akson API (Go Implementation)

A chat-based assistant framework written in Go, converted from the original Python implementation.

## Features

- **REST API**: Full HTTP API compatible with the original Python version
- **Real-time Streaming**: Server-Sent Events for live message updates  
- **Assistant Framework**: Pluggable assistant system with LLM integration
- **Anthropic Claude**: Direct integration with Claude API (no abstraction layer)
- **Chat Persistence**: JSON-based chat state persistence
- **Docker Support**: Containerized deployment with Docker Compose

## Architecture

- **HTTP Server**: Built with Go stdlib `net/http` (no external framework)
- **LLM Integration**: Direct Anthropic Claude API client
- **Streaming**: Custom SSE implementation using `http.Flusher`
- **Models**: JSON serialization with Go structs
- **Registry**: Dynamic assistant discovery and loading

## Getting Started

### Prerequisites

- Go 1.23+
- Anthropic API key
- Docker (optional)

### Environment Setup

1. Copy the environment file:
```bash
cp .env.example .env
```

2. Set your Anthropic API key in `.env`:
```bash
ANTHROPIC_API_KEY=your_api_key_here
```

### Running Locally

```bash
# Build and run
go build ./cmd/api
./api

# Or run directly
go run ./cmd/api
```

The API will be available at `http://localhost:8000`

### Running with Docker

```bash
# From the project root
docker compose up --build --watch
```

## API Endpoints

### Health
- `GET /health` - Health check

### Assistants  
- `GET /assistants` - List available assistants

### Chats
- `GET /chats` - List all chats
- `GET /chats/{id}` - Get chat state
- `POST /chats/{id}/messages` - Send message
- `GET /chats/{id}/events` - SSE stream for real-time updates
- `PUT /chats/{id}/assistant` - Set chat assistant
- `PUT /chats/{id}/messages/{messageId}` - Edit message
- `DELETE /chats/{id}/messages/{messageId}` - Delete message
- `DELETE /chats/{id}` - Delete chat

### Chat Commands
- `/clear` - Clear chat history
- `/assistant <name>` - Switch assistant

## Project Structure

```
api-go/
├── cmd/api/           # HTTP server entry point
├── internal/
│   ├── models/        # Data models (Chat, Message, etc.)
│   ├── handlers/      # HTTP request handlers
│   ├── framework/     # LLM assistant framework
│   ├── registry/      # Assistant discovery & loading
│   └── streaming/     # Real-time SSE implementation
├── pkg/akson/         # Public API interfaces
└── assistants/       # Assistant implementations
```

## Testing

```bash
# Run all tests
go test ./...

# Run specific package tests
go test ./internal/models
```

## Environment Variables

- `ANTHROPIC_API_KEY` - Required: Anthropic API key
- `DEFAULT_MODEL` - Claude model name (default: claude-3-5-sonnet-20241022)
- `DEFAULT_ASSISTANT` - Default assistant name (default: Claude)
- `ALLOW_ORIGINS` - CORS allowed origins (default: *)
- `CHATS_DIR` - Chat storage directory (default: chats)
- `PORT` - Server port (default: 8000)

## Migration from Python

This Go implementation maintains full API compatibility with the Python version:

- Same REST endpoints and JSON schemas
- Compatible chat persistence format  
- Identical WebSocket/SSE streaming protocol
- Docker Compose setup works unchanged

The main differences:
- Uses Anthropic API directly (no LiteLLM abstraction)
- Built with Go stdlib `net/http` (no FastAPI)
- Custom SSE implementation vs sse-starlette

## Contributing

1. Follow Go conventions and use `go fmt`
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure Docker build works

## License

MIT License - see LICENSE file for details