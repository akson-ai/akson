from framework import SimpleAssistant
from function_calling import MCPToolkit

vault = "/Users/cenk/Library/Mobile Documents/iCloud~md~obsidian/Documents/my-vault"

obsidian = SimpleAssistant(
    name="Obsidian",
    system_prompt="You are Obsidian assistant.",
    toolkit=MCPToolkit(
        command="npx",
        args=["-y", "mcp-obsidian", vault],
    ),
)
