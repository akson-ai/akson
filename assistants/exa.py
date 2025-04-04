import os

from exa_py import Exa as ExaClient

from framework import DeclarativeAssistant

client = ExaClient(os.environ["EXA_API_KEY"])


class Exa(DeclarativeAssistant):
    """
    You are Exa assistant.

    Exa finds the exact content you’re looking for on the web.

    """

    def search(self, query: str) -> str:
        """
        The search endpoint lets you intelligently search the web and extract contents from the results.

        By default, it automatically chooses between traditional keyword search and Exa’s embeddings-based model, to find the most relevant results for your query.

        Args:
          query (str): The query to search for

        Returns:
          str: The search results

        """
        results = client.search_and_contents(query, text=True)
        return str(results)

    def contents(self, urls: list[str]) -> str:
        """
        Get the full page contents, summaries, and metadata for a list of URLs.

        Returns instant results from our cache, with automatic live crawling as fallback for uncached pages.

        Args:
          urls (list[str]): The URLs to get contents for

        Returns:
          str: The contents

        """
        results = client.get_contents(urls=urls, text=True)
        return str(results)

    def find_similar(self, url: str) -> str:
        """
        Find similar links to the link provided and optionally return the contents of the pages.

        Args:
          url (str): The URL to find similar links for

        Returns:
          str: The similar links

        """
        results = client.find_similar_and_contents(url=url, text=True)
        return str(results)

    def answer(self, question: str) -> str:
        """
        Get an LLM answer to a question informed by Exa search results. Fully compatable with OpenAI’s chat completions endpoint - docs here.

        answer performs an Exa search and uses an LLM (GPT-4o-mini) to generate either:

            A direct answer for specific queries. (i.e. “What is the capital of France?” would return “Paris”)
            A detailed summary with citations for open-ended queries (i.e. “What is the state of ai in healthcare?” would return a summary with citations to relevant sources)

        The response includes both the generated answer and the sources used to create it.

        Args:
          question (str): The question to answer

        Returns:
          str: The answer

        """
        results = client.answer(question, text=True)
        return str(results)


exa = Exa()
