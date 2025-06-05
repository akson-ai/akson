"""
framework package contains utilities for building assistants.
"""

from .agent import Agent
from .function_calling import MCPToolkit  # TODO: delete
from .function_calling import (
    AssistantToolkit,
    FastMCPToolkit,
    FunctionToolkit,
    MultiToolkit,
    Toolkit,
)

__all__ = [
    "Agent",
    "Toolkit",
    "MultiToolkit",
    "FunctionToolkit",
    "AssistantToolkit",
    "MCPToolkit",
    "FastMCPToolkit",
]
