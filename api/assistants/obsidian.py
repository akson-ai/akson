from framework import Agent, MCPToolkit

# TODO get vault from env var
vault = "/Users/cenk/Library/Mobile Documents/iCloud~md~obsidian/Documents/my-vault"

obsidian = Agent(
    name="Obsidian",
    system_prompt="You are Obsidian assistant.",
    toolkit=MCPToolkit.from_config(
        command="npx",
        args=["-y", "mcp-obsidian", vault],
    ),
)
