import os
import re
import time
import uuid
from datetime import datetime
from typing import Optional

from litellm import CustomStreamWrapper, acompletion
from litellm.types.utils import Message
from pydantic import BaseModel

from akson import Assistant, Chat
from logger import logger

from .function_calling import FunctionToolkit, Toolkit
from .streaming import MessageBuilder


class Agent(Assistant):
    """Provides an Assistant implementation with a given system prompt and toolkit."""

    def __init__(
        self,
        name: str,
        model: str = os.environ["DEFAULT_MODEL"],
        system_prompt: Optional[str] = None,
        output_type: Optional[type[BaseModel]] = None,
        toolkit: Optional[Toolkit] = None,
        max_turns: int = 10,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.output_type = output_type
        self.toolkit = toolkit
        self.max_turns = max_turns
        self.examples: list[tuple[str, BaseModel]] = []
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def respond(self, user_message: str) -> str | BaseModel:
        chat = Chat.temp()
        chat.state.messages.append(
            Message(
                id=str(uuid.uuid4()),
                role="user",  # type: ignore
                content=user_message,
            )
        )
        await self.run(chat)

        if chat._structured_output:
            return chat._structured_output
        else:
            return chat.state.messages[-1]["content"]

    async def run(self, chat: Chat) -> None:
        logger.info("Running assistant %s", self.name)

        # These messages are sent to the LLM API, prefixed by the system prompt.
        messages = self._get_messages(chat)

        def append_messages(message: Message):
            assert message["id"]
            assert message["name"]
            messages.append(message)
            chat.state.messages.append(message)
            chat.state.save_to_disk()

        async def handle_tool_calls(message: Message):
            assert self.toolkit
            assert message.tool_calls
            tool_messages = await self.toolkit.handle_tool_calls(message.tool_calls)
            for tool_message in tool_messages:
                message_id = await chat.begin_message("tool")
                tool_message["id"] = message_id
                tool_message["name"] = self.name
                append_messages(tool_message)
                assert tool_message.content
                await chat.add_chunk("content", tool_message.content)

        # We start by sending the first message.
        message = await self._complete(messages, chat)
        append_messages(message)

        # We keep continue hitting OpenAI API until there are no more tool calls.
        current_turn = 0
        while message.tool_calls:
            current_turn += 1
            if current_turn > self.max_turns:
                raise Exception(f"Max turns ({self.max_turns}) exceeded")

            await handle_tool_calls(message)

            # Send messages with tool calls.
            message = await self._complete(messages, chat)
            append_messages(message)

    async def _complete(self, messages: list[Message], chat: Chat) -> Message:
        # Replace invalid characters in assistant name
        for message in messages:
            if hasattr(message, "name"):
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
            **kwargs,
        )
        assert isinstance(response, CustomStreamWrapper)

        # We start by sending a begin_message event to the web client.
        # This will cause the web client to draw a new message box for the assistant.
        message_id = await chat.begin_message("assistant")

        # We will aggregate delta messages and store them in this variable until we see a finish_reason.
        # This is the only way to get the full content of the message.
        # We'll return this value at the end of the function.
        builder = MessageBuilder(message_id, self.name)

        async for chunk in response:
            assert chunk.__class__.__name__ == "ModelResponseStream"
            assert len(chunk.choices) == 1
            choice = chunk.choices[0]
            events = builder.write(choice.delta)
            for event in events:
                await chat.add_chunk(event.name, event.chunk)

            if finish_reason := choice.finish_reason:
                message = builder.getvalue()
                if finish_reason == "stop":
                    if self.output_type:
                        assert isinstance(message.content, str)
                        instance = self.output_type.model_validate_json(message.content)
                        await chat.set_structured_output(instance)
                elif finish_reason == "tool_calls":
                    pass
                else:
                    raise NotImplementedError(f"finish_reason={finish_reason}")

                return message

        raise Exception("Stream ended unexpectedly")

    def _get_messages(self, chat: Chat) -> list[Message]:
        messages: list[Message] = []

        messages.append(
            Message(
                role="system",  # type: ignore
                content=self._get_system_prompt(),
            )
        )

        for user_message, response in self.examples:
            messages.extend(
                [
                    Message(
                        role="system",  # type: ignore
                        name="example_user",
                        content=user_message,
                    ),
                    Message(
                        role="system",  # type: ignore
                        name="example_assistant",
                        content=response.model_dump_json(),
                    ),
                ]
            )

        messages.extend(chat.state.messages)
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


class ClassAgent(Agent):
    """
    A base class for agents implemented as classes.
    This provides an alternative method for defining an agent.
    Directly constructing an `Agent` object without using this class is perfectly fine.

    How it works:
    - Docstring becomes system prompt.
    - Attributes are passed to `Agent` constructor.
    - Methods become function tools.

    Example:

        class Mathematician(ClassAgent):
            "You can answer questions about math. Use provided function to add two numbers."

            model = "claude-3-7-sonnet-latest"

            def add_two_numbers(self, a: int, b: int) -> int:
                return a + b
    """

    def __init__(self):
        name = self.__class__.__name__
        system_prompt = self.__doc__ or ""
        toolkit = FunctionToolkit([val for val in self.__class__.__dict__.values() if callable(val)])
        is_member = lambda x: not x[0].startswith("_") and not callable(x[1]) and not isinstance(x[1], property)
        kwargs = dict(filter(is_member, self.__class__.__dict__.items()))
        super().__init__(name=name, system_prompt=system_prompt, toolkit=toolkit, **kwargs)
