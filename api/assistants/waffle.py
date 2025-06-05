from fastmcp import Client as FastMCPClient

from akson import Chat, Message
from framework import (
    Agent,
    AssistantToolkit,
    FunctionToolkit,
    MCPToolkit,
    MultiToolkit,
)

system_prompt = f"""
    You are Waffle, a personal AI assistant.

    You should primarily rely on your built-in knowledge to answer questions.
    Only use web search when:
    1. The information is likely to be outdated due to your knowledge cutoff date
    2. The information is dynamic and changes frequently (like current events, weather, or live data)
    3. The user explicitly requests current information
    For all other queries, use your existing knowledge to provide accurate and helpful responses.
"""


async def find_movie(name: str) -> str:
    """
    Use this tool to find and download movies.

    Args:
      name (str): The name of the movie

    Returns:
      str: Web page URL of the movie
    """
    from deps import registry

    assistant = registry.get_assistant("Movie")
    chat = Chat()
    chat.state.messages.append(
        Message(
            role="user",
            content=f"I want to watch {name}. Find and download the movie.",
        )
    )
    await assistant.run(chat)
    return chat.state.messages[-1].content


assistant = Agent(
    name="Waffle",
    model="claude-sonnet-4-20250514",
    system_prompt=system_prompt,
    toolkit=MultiToolkit(
        [
            FunctionToolkit([find_movie]),
            AssistantToolkit(["WebSearch", "Gmail"]),
            MCPToolkit(
                FastMCPClient(
                    {
                        "mcpServers": {
                            "fetch": {
                                "command": "uvx",
                                "args": ["mcp-server-fetch"],
                            },
                            "sequential-thinking": {
                                "command": "npx",
                                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
                            },
                        }
                    }
                )
            ),
        ],
    ),
)
