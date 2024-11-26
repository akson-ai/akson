import os
from abc import ABC, abstractmethod
from textwrap import dedent
from typing import Any, Generator

import gradio as gr
from openai import AzureOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import (
    Function as ToolFunction,
)

from function_calling import Function, Toolset
from logger import logger


class Agent(ABC):

    name: str
    """Name of the agent. Must be unique. Other agents use this name to refer to it."""

    description: str
    """Description of the agent. It tells what the agent can do. Used during planning."""

    def __repr__(self):
        return f"Agent<{self.name}>"

    @abstractmethod
    def message(self, input: str) -> Generator[str | gr.Image, None, None]:
        """Sends a message to the agent. Agents should remember previous messages."""


class SimpleAgent(Agent):

    prompt: str
    """Prompt for the agent. They are instructions for the agent. """

    tools: list[type[Function]] = []
    """List of tools the agent can use."""

    def __init__(self):
        super().__init__()

        self.toolset = Toolset(self, *self.tools)
        self.description = dedent(self.description)
        self.prompt = dedent(self.prompt)
        self.client = AzureOpenAI()
        self.messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=self.prompt)
        ]

    def message(self, input: str) -> Generator[str | gr.Image, None, None]:
        completion = self._complete(ChatCompletionUserMessageParam(role="user", content=input))
        tool_calls = self.toolset.process_response(completion, agent=self.name)
        while tool_calls:
            completion = self._complete(*tool_calls)
            tool_calls = self.toolset.process_response(completion, agent=self.name)

        content = completion.choices[0].message.content
        assert isinstance(content, str)
        yield content

    def _complete(self, *messages: ChatCompletionMessageParam) -> ChatCompletion:
        self.messages.extend(messages)

        logger.info("Completing chat for %s", self.name)
        for message in self.messages:
            logger.debug(message)

        completion = self.client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=self.messages,
            **self._tool_kwargs(),
        )

        message = completion.choices[0].message
        logger.info("%s: %s", self.name, message.content)
        self.messages.append(_convert_assistant_message(message))

        return completion

    def _tool_kwargs(self) -> dict[str, Any]:
        tools = self.toolset.openai_schema()
        if tools:
            return {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
        return {}


def _convert_assistant_message(message: ChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
    if message.tool_calls:
        tool_calls = list(map(_convert_tool_call, message.tool_calls))
        return ChatCompletionAssistantMessageParam(role=message.role, content=message.content, tool_calls=tool_calls)
    else:
        return ChatCompletionAssistantMessageParam(role=message.role, content=message.content)


def _convert_tool_call(tool_call: ChatCompletionMessageToolCall) -> ChatCompletionMessageToolCallParam:
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        function=ToolFunction(
            name=tool_call.function.name,
            arguments=tool_call.function.arguments,
        ),
        type=tool_call.type,
    )
