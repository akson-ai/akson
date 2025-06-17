package database

import (
	"context"
	"fmt"
	"log/slog"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/pressly/goose/v3"

	_ "github.com/jackc/pgx/v5/stdlib" // PostgreSQL driver for goose
)

// Config holds database configuration
type Config struct {
	Host     string
	Port     string
	User     string
	Password string
	Database string
	SSLMode  string
}

// LoadConfig loads database configuration from environment variables
func LoadConfig() *Config {
	return &Config{
		Host:     getEnv("DB_HOST", "localhost"),
		Port:     getEnv("DB_PORT", "5432"),
		User:     getEnv("DB_USER", "akson"),
		Password: getEnv("DB_PASSWORD", "akson"),
		Database: getEnv("DB_NAME", "akson"),
		SSLMode:  getEnv("DB_SSLMODE", "disable"),
	}
}

// DSN returns the database connection string
func (c *Config) DSN() string {
	return fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		c.Host, c.Port, c.User, c.Password, c.Database, c.SSLMode,
	)
}

// PostgresDSN returns the postgres-specific DSN for goose
func (c *Config) PostgresDSN() string {
	return fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=%s",
		c.User, c.Password, c.Host, c.Port, c.Database, c.SSLMode,
	)
}

// Connect creates a new database connection pool
func Connect(ctx context.Context, config *Config) (*pgxpool.Pool, error) {
	dsn := config.DSN()
	
	poolConfig, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to parse database config: %w", err)
	}

	// Configure connection pool
	poolConfig.MaxConns = 25
	poolConfig.MinConns = 5

	pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create database pool: %w", err)
	}

	// Test the connection
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	slog.Info("Database connection established", "host", config.Host, "database", config.Database)
	return pool, nil
}

// RunMigrations runs database migrations using goose
func RunMigrations(config *Config, migrationsDir string) error {
	dsn := config.PostgresDSN()
	
	// Set up goose
	if err := goose.SetDialect("postgres"); err != nil {
		return fmt.Errorf("failed to set goose dialect: %w", err)
	}

	// Run migrations
	db, err := goose.OpenDBWithDriver("postgres", dsn)
	if err != nil {
		return fmt.Errorf("failed to open database for migrations: %w", err)
	}
	defer db.Close()

	if err := goose.Up(db, migrationsDir); err != nil {
		return fmt.Errorf("failed to run migrations: %w", err)
	}

	slog.Info("Database migrations completed", "migrationsDir", migrationsDir)
	return nil
}

// getEnv gets an environment variable or returns a default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}