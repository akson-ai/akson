import os
import pathlib

from akson import Chat, Message
from framework import Agent, AssistantToolkit, FunctionToolkit, MultiToolkit

PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]

# Load the Perplexity prompt guide from the markdown file
# Genrated with r.jina.ai/https://docs.perplexity.ai/guides/prompt-guide
prompt_guide_path = pathlib.Path(__file__).parent / "prompts" / "perplexity_prompt_guide.md"
with open(prompt_guide_path, "r") as f:
    perplexity_prompt_guide = f.read()

system_prompt = f"""
    You are Waffle, a personal AI assistant.

    You should primarily rely on your built-in knowledge to answer questions.
    Only use web search when:
    1. The information is likely to be outdated due to your knowledge cutoff date
    2. The information is dynamic and changes frequently (like current events, weather, or live data)
    3. The user explicitly requests current information
    For all other queries, use your existing knowledge to provide accurate and helpful responses.

    {perplexity_prompt_guide}
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
    system_prompt=system_prompt,
    toolkit=MultiToolkit(
        [
            FunctionToolkit([find_movie]),
            AssistantToolkit(["WebSearch"]),
        ],
    ),
)
