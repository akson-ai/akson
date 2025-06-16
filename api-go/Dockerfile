# Multi-stage build for Go application
FROM golang:1.23-alpine AS builder

# Install git for go modules
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main ./cmd/api

# Final stage - debugging-friendly image
FROM ubuntu:22.04

# Install essential tools for debugging and MCP integration
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    vim \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/main .

# Create chats directory
RUN mkdir -p chats

# Expose port
EXPOSE 8000

# Run the application
CMD ["./main"]