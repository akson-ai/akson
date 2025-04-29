# Akson Compose

## Overview
Akson Compose is a Docker Compose configuration that brings together all Akson components into a single, easy-to-deploy package.
This project makes it simple to get started with Akson by providing a unified setup for all services.

## Components
This project includes the following Akson components:
- [akson-api](https://github.com/akson-ai/akson-api): The core backend service
- [akson-web](https://github.com/akson-ai/akson-web): The web interface
- [akson-cli](https://github.com/akson-ai/akson-cli): The command-line interface

## Prerequisites

Before you begin, ensure you have the following installed:
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0.0 or later)

## Getting Started

Follow these steps to get Akson up and running:

1. Clone the repository:
   ```bash
   git clone https://github.com/akson-ai/akson-compose.git
   cd akson-compose
   ```

2. Initialize the submodules:
   ```bash
   git submodule update --init
   ```

3. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

   Then, open `.env` and configure your API keys and other environment variables as needed.

4. Start the services:
   ```bash
   docker compose up --build --watch
   ```

5. Access the services:
   - Web Interface: [http://localhost:5173](http://localhost:5173)
   - API: [http://localhost:8000](http://localhost:8000)

6. (Optional) To run the CLI tool:
   ```bash
   docker compose run --build --rm cli
   ```

## What You Can Do

Once the services are running, you can:
- Interact with AI assistants through the web interface or CLI
- Use the API to integrate assistants into your applications