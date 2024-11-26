"""
Global registry for agents.
"""

from agent import Agent

# Global dictionary of registered agents.
agents: dict[str, type[Agent]] = {}


def register(agent: type[Agent]):
    agents[agent.name] = agent


def get(name: str) -> type[Agent]:
    return agents[name]


def list() -> list[type[Agent]]:
    """Returns a list of all registered agents that can be used by Planner agent."""
    return [agent for agent in agents.values()]
