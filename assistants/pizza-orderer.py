from framework import SimpleAssistant
from function_calling import MCPToolkit

pizza_orderer = SimpleAssistant(
    name="Pizza Orderer",
    system_prompt="You are an AI assistant that can order pizza over the phone.",
    toolkit=MCPToolkit(
        command="uv",
        args=["run", "python", "mcp-servers/bland.py"],
    ),
)
