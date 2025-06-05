from framework import Agent, MCPToolkit

pizza_orderer = Agent(
    name="Pizza Orderer",
    system_prompt="You are an AI assistant that can order pizza over the phone.",
    toolkit=MCPToolkit.from_config(
        command="uv",
        args=["run", "python", "mcp-servers/bland.py"],
    ),
)
