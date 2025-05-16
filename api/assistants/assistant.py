from framework import Agent, FunctionToolkit

system_prompt = """
    You are a personal AI assistant.

    You should primarily rely on your built-in knowledge to answer questions.
    Only use web search when:
    1. The information is likely to be outdated due to your knowledge cutoff date
    2. The information is dynamic and changes frequently (like current events, weather, or live data)
    3. The user explicitly requests current information
    For all other queries, use your existing knowledge to provide accurate and helpful responses.
"""


def search_web(query: str) -> str:
    """
    Use this function to search the web.

    Args:
      query (str): The query to search for

    Returns:
      str: The search results
    """
    return "TODO"


def browser_use(url: str, action: str) -> str:
    """
    Use this function to interact with a web browser.

    Args:
      url (str): The URL to interact with
      action (str): The action to perform (e.g., 'navigate', 'click', 'type')

    Returns:
      str: The result of the browser interaction
    """
    return "TODO"


assistant = Agent(
    name="Assistant",
    system_prompt=system_prompt,
    toolkit=FunctionToolkit([search_web, browser_use]),
)
