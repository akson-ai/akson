import os

from exa_py.api import Exa
from langchain_core.tools import tool


@tool
def search_web(query: str):
    """Search the web for relevant information."""

    exa = Exa(os.environ["EXA_API_KEY"])

    response = exa.search_and_contents(
        query,
        num_results=10,
        use_autoprompt=True,
        summary=True,
    )

    return [
        {
            "title": result.title,
            "url": result.url,
            "summary": result.summary,
        }
        for result in response.results
    ]
