from framework import Agent, AssistantToolkit

agent = Agent(
    name="WebSearch",
    system_prompt="""
    You are a web search assistant.
    When you are asked to do a task, you should first try to use Perplexity to search the web.
    If Perplexity cannot answer the question, you should use Exa to search the web.
    """,
    # TODO parent agent don't have access to sub-agent descriptions
    toolkit=AssistantToolkit(["Perplexity", "Exa"]),
)
