import os
import pathlib

import httpx

from framework import Agent, FunctionToolkit

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


async def search_web(query: str) -> str:
    """
    Use this function to search the web.

    Args:
      query (str): The query to search for

    Returns:
      str: The search results
    """
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar",  # https://docs.perplexity.ai/guides/model-cards
        "messages": [
            {
                "role": "user",
                "content": query,
            },
        ],
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except Exception:
            print(f"status: {response.status_code}, text: {response.text}")
            raise

        data = response.json()
        message = data["choices"][0]["message"]
        content = message["content"]
        citations = "\n".join(f"{i}. {citation}" for i, citation in enumerate(data["citations"], 1))
        return f"{content}\n\n{citations}"


assistant = Agent(
    name="Waffle",
    system_prompt=system_prompt,
    toolkit=FunctionToolkit([search_web]),
)
