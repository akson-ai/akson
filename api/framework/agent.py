import os
import re
import time
from datetime import datetime
from typing import Optional

import litellm
from langfuse.decorators import langfuse_context
from litellm import ChatCompletionMessageToolCall as LitellmToolCall
from litellm import CustomStreamWrapper
from litellm import Message as LitellmMessage
from litellm import acompletion
from litellm.types.utils import Function as LitellmFunction
from litellm.types.utils import Message as LitellmMessage
from pydantic import BaseModel

from akson import Assistant, Chat, Message, ToolCall
from logger import logger

from .function_calling import Toolkit
from .streaming import MessageBuilder

DEFAULT_MODEL = os.environ["DEFAULT_MODEL"]

litellm.drop_params = True
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]


class Agent(Assistant):
    """Provides an Assistant implementation with a given system prompt and toolkit."""

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None,
        output_type: Optional[type[BaseModel]] = None,
        toolkit: Optional[Toolkit] = None,
        max_turns: int = 10,
    ):
        """
        Creates a new Agent.
        """
        self.name = name
        self.description = description
        self.model = model
        self.system_prompt = system_prompt
        self.output_type = output_type
        self.toolkit = toolkit
        self.max_turns = max_turns
        self.examples: list[tuple[str, BaseModel]] = []

    async def run(self, chat: Chat) -> None:
        logger.info("Running assistant %s", self.name)

        # These messages are sent to the LLM API, prefixed by the system prompt.
        messages = self._get_messages(chat)

        async def handle_tool_calls(message: LitellmMessage):
            assert self.toolkit
            assert message.tool_calls
            tool_messages = await self.toolkit.handle_tool_calls(message.tool_calls)
            for tool_message in tool_messages:
                messages.append(tool_message)
                reply = await chat.reply("tool", name=self.name)
                if tool_message.content:
                    await reply.add_chunk(tool_message.content)
                await reply.add_chunk(tool_message["tool_call_id"], field="tool_call_id")
                await reply.end()

        # We start by sending the first message.
        message = await self._complete(messages, chat)
        messages.append(message)

        # We keep continue hitting OpenAI API until there are no more tool calls.
        current_turn = 0
        while message.tool_calls:
            current_turn += 1
            if current_turn > self.max_turns:
                raise Exception(f"Max turns ({self.max_turns}) exceeded")

            await handle_tool_calls(message)

            # Send messages with tool calls.
            message = await self._complete(messages, chat)
            messages.append(message)

    async def _complete(self, messages: list[LitellmMessage], chat: Chat) -> LitellmMessage:
        # Replace invalid characters in assistant name
        for message in messages:
            if message.get("name"):
                message["name"] = re.sub(r"[^a-zA-Z0-9-]", "_", message["name"])

        logger.info("Completing chat")
        for message in messages:
            logger.debug(message)

        kwargs = {}
        if self.toolkit:
            tools = await self.toolkit.get_tools()
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
                kwargs["parallel_tool_calls"] = False

        if self.output_type:
            kwargs["response_format"] = self.output_type

        response = await acompletion(
            model=self.model,
            messages=messages,
            stream=True,
            metadata={
                "existing_trace_id": langfuse_context.get_current_trace_id(),
                "parent_observation_id": langfuse_context.get_current_observation_id(),
            },
            **kwargs,
        )
        assert isinstance(response, CustomStreamWrapper)

        # We start by sending a begin_message event to the web client.
        # This will cause the web client to draw a new message box for the assistant.
        reply = await chat.reply("assistant", name=self.name)

        # We will aggregate delta messages and store them in this variable until we see a finish_reason.
        # This is the only way to get the full content of the message.
        # We'll return this value at the end of the function.
        builder = MessageBuilder()

        # We will return this value at the end of the function.
        message: Optional[LitellmMessage] = None

        # Do not break this loop. Otherwise, litellm will not be able to run callbacks.
        async for chunk in response:
            assert chunk.__class__.__name__ == "ModelResponseStream"
            assert len(chunk.choices) == 1
            choice = chunk.choices[0]
            events = builder.write(choice.delta)
            for event in events:
                await reply.add_chunk(event.chunk, field=event.name)

            if finish_reason := choice.finish_reason:
                message = builder.getvalue()
                if finish_reason not in ("stop", "tool_calls"):
                    raise NotImplementedError(f"finish_reason={finish_reason}")
                await reply.end()

        if not message:
            raise Exception("Stream ended unexpectedly")

        return message

    def _get_messages(self, chat: Chat) -> list[LitellmMessage]:
        messages: list[LitellmMessage] = []

        messages.append(
            LitellmMessage(
                role="system",  # type: ignore
                content=self._get_system_prompt(),
            )
        )

        for user_message, response in self.examples:
            messages.extend(
                [
                    LitellmMessage(
                        role="system",  # type: ignore
                        name="example_user",
                        content=user_message,
                    ),
                    LitellmMessage(
                        role="system",  # type: ignore
                        name="example_assistant",
                        content=response.model_dump_json(),
                    ),
                ]
            )

        messages.extend([message_to_litellm(message) for message in chat.state.messages])
        return messages

    def _get_system_prompt(self) -> str:
        prompt = self.system_prompt or ""
        if prompt:
            prompt += "\n\n"

        t = datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p")
        o = time.strftime("%z")  # Timezone offset
        prompt += f"Today's date and time is {t} ({o})"

        return prompt

    def add_example(self, user_message: str, response: BaseModel):
        """Add an example to the prompt."""
        self.examples.append((user_message, response))


def tool_call_from_litellm(tool_call: LitellmToolCall):
    return ToolCall(
        id=tool_call.id,
        name=tool_call.function.name or "",
        arguments=tool_call.function.arguments,
    )


def tool_call_to_litellm(self: ToolCall):
    return LitellmToolCall(
        id=self.id,
        function=LitellmFunction(name=self.name, arguments=self.arguments),
    )


def message_from_litellm(message: LitellmMessage, *, name: str):
    tool_call = None
    if message.tool_calls:
        assert len(message.tool_calls) == 1
        tool_call = tool_call_from_litellm(message.tool_calls[0])
    return Message(
        role=message.role,  # type: ignore
        name=name,
        content=message.content or "",
        tool_call=tool_call,
        tool_call_id=message.get("tool_call_id"),
    )


def message_to_litellm(self: Message):
    if self.tool_call:
        tool_calls = [tool_call_to_litellm(self.tool_call)]
    else:
        tool_calls = None
    return LitellmMessage(
        id=self.id,
        role=self.role,  # type: ignore
        name=self.name,
        content=self.content,
        tool_calls=tool_calls,
        tool_call_id=self.tool_call_id,
    )
