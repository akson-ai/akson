# Akson

## Overview
Akson is a runtime platform for AI agents, similar to how web servers run web applications. It provides the infrastructure and environment for running, managing, and interacting with various AI agents through text and voice interfaces.

The project is currently in its early prototype stage.

## Core Design
- Platform acts as a runtime environment for AI agents
- No built-in agents in base distribution
- Text and voice-based interaction with agents
- Core system agents:
  - Assistant Agent for routing requests
  - Planner Agent for coordinating tasks

## Agent Development
- Framework-agnostic implementation
- Only requirement is a simple interface:
  ```python
  def message(input: str) -> str
  ```
- Agents are distributed through GitHub repositories, similar to Go's package management system

## Feedback & Suggestions
While the project is not accepting code contributions at this time, feedback and suggestions are welcome! Feel free to:
- Open issues for feature suggestions
- Share ideas for potential use cases
- Provide feedback on the current architecture and design
- Discuss potential agent ideas

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.