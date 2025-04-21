from framework import MCPToolkit, SimpleAssistant

gmail = SimpleAssistant(
    name="Gmail",
    system_prompt="You are Gmail assistant. Try bringing 100 results when searching for emails. Get confirmation before performing any actions that modify data.",
    toolkit=MCPToolkit(
        command="npx",
        args=["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
    ),
)
