import os
import re
import time
from datetime import datetime
from typing import Any, Optional, Sequence

from openai import AsyncOpenAI
from openai.lib.streaming.chat import (
    ChunkEvent,
    ContentDeltaEvent,
    FunctionToolCallArgumentsDeltaEvent,
    RefusalDeltaEvent,
)
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ParsedChatCompletionMessage,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function
from pydantic import BaseModel

from akson import Assistant, Chat, ChatState
from function_calling import FunctionToolkit, Toolkit
from logger import logger


class SimpleAssistant(Assistant):
    """Simple assistant that uses OpenAI's chat API to generate responses."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        output_type: Optional[type[BaseModel]] = None,
        toolkit: Optional[Toolkit] = None,
        max_turns: int = 10,
    ):
        self.system_prompt = system_prompt
        self.output_type = output_type
        self.toolkit = toolkit
        self.max_turns = max_turns
        self.examples: list[tuple[str, BaseModel]] = []
        self._name = name
        self._client = AsyncOpenAI()

    @property
    def name(self) -> str:
        return self._name

    async def respond(self, user_message: str) -> str | BaseModel:
        state = ChatState(id="temp", messages=[])
        # TODO generate id automatically
        # TODO generate name automatically (is name really required?)
        state.messages.append(
            {"id": "asldkfjaslkfj", "role": "assistant", "name": "asldkjlkfaj", "content": user_message}
        )
        chat = Chat(state)
        # TODO why setting _assistant needed before run() ?
        chat._assistant = self
        await self.run(chat)
        if self.output_type:
            assert isinstance(chat._structured_output, self.output_type)
            return chat._structured_output

        return chat.state.messages[-1]["content"]

    async def run(self, chat: Chat) -> None:
        logger.debug(f"Completing chat...\nLast message: {chat.state.messages[-1]}")

        # These messages are sent to OpenAI in chat completion request.
        # Here, we convert chat messages in web UI to OpenAI format.
        messages = self._get_openai_messages(chat)

        message = await self._complete(messages, chat)
        messages.append(_convert_assistant_message(message))

        # We keep continue hitting OpenAI API until there are no more tool calls.
        current_turn = 0
        if self.toolkit:
            while message.tool_calls:
                current_turn += 1
                if current_turn > self.max_turns:
                    raise Exception(f"Max turns ({self.max_turns}) exceeded")

                tool_calls = await self.toolkit.handle_tool_calls(message.tool_calls)
                messages.extend(tool_calls)

                message = await self._complete(messages, chat)
                messages.append(_convert_assistant_message(message))

    def _get_openai_messages(self, chat: Chat) -> list[ChatCompletionMessageParam]:
        messages: Sequence[ChatCompletionMessageParam] = []
        messages.append(ChatCompletionSystemMessageParam(role="system", content=self._get_system_prompt()))
        for user_message, response in self.examples:
            messages.extend(
                [
                    {"role": "system", "name": "example_user", "content": user_message},
                    {"role": "system", "name": "example_assistant", "content": response.model_dump_json()},
                ]
            )
        for message in chat.state.messages:
            if message.get("category"):
                continue
            if message["role"] == "user":
                messages.append(
                    ChatCompletionUserMessageParam(role="user", name=message["name"], content=message["content"])
                )
            elif message["role"] == "assistant":
                messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant", name=message["name"], content=message["content"]
                    )
                )
        return messages

    def _get_system_prompt(self) -> str:
        t = datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p")
        o = time.strftime("%z")  # Timezone offset
        return f"{self.system_prompt}\n\nToday's date and time is {t} ({o})."

    async def _complete(self, messages: list[ChatCompletionMessageParam], chat: Chat) -> ParsedChatCompletionMessage:
        logger.info("Completing chat")
        for message in messages:
            if "name" in message:
                message["name"] = re.sub(r"[^a-zA-Z0-9_-]", "_", message["name"])
            logger.debug(message)

        # Because we're streaming, we need to track whether a message has started or not.
        message_started = False

        kwargs = {}
        if self.toolkit:
            tools = await self.toolkit.get_tools()
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
                kwargs["parallel_tool_calls"] = False

        if self.output_type:
            kwargs["response_format"] = self.output_type

        async with self._client.beta.chat.completions.stream(
            model=os.environ["OPENAI_MODEL"],
            messages=messages,
            **kwargs,
        ) as stream:
            async for event in stream:
                match event:  # https://github.com/openai/openai-python/blob/main/helpers.md#chat-completions-events
                    case ContentDeltaEvent():
                        if not message_started:
                            message_started = True
                            await chat.begin_message()
                        await chat.add_chunk(event.delta)
                    case RefusalDeltaEvent():
                        if not message_started:
                            message_started = True
                            await chat.begin_message()
                        await chat.add_chunk(event.delta)
                    case FunctionToolCallArgumentsDeltaEvent():
                        if not message_started:
                            message_started = True
                            await chat.begin_message(category="info")
                            await chat.add_chunk(f"Calling function: {event.name}(")
                        await chat.add_chunk(event.arguments_delta)
                    case ChunkEvent() if event.chunk.choices[0].finish_reason:
                        choice = event.snapshot.choices[0]
                        if choice.finish_reason == "tool_calls":
                            await chat.add_chunk(")")
                        await chat.end_message()
                        if choice.finish_reason not in ("stop", "tool_calls"):
                            raise NotImplementedError(f"finish_reason={choice.finish_reason}")
                        if self.output_type:
                            assert isinstance(choice.message.parsed, self.output_type)
                            await chat.set_structured_output(choice.message.parsed)
                        return choice.message

        raise Exception("Stream ended unexpectedly")

    async def _tool_kwargs(self) -> dict[str, Any]:
        if not self.toolkit:
            return {}
        tools = await self.toolkit.get_tools()
        if not tools:
            return {}
        return {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}

    def add_example(self, user_message: str, response: BaseModel):
        """Add an example to the prompt."""
        self.examples.append((user_message, response))


def _convert_assistant_message(message: ParsedChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
    if message.tool_calls:
        tool_calls = list(map(_convert_tool_call, message.tool_calls))
        return ChatCompletionAssistantMessageParam(role="assistant", content=message.content, tool_calls=tool_calls)
    else:
        return ChatCompletionAssistantMessageParam(role="assistant", content=message.content)


def _convert_tool_call(tool_call: ChatCompletionMessageToolCall) -> ChatCompletionMessageToolCallParam:
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        function=Function(
            name=tool_call.function.name,
            arguments=tool_call.function.arguments,
        ),
        type=tool_call.type,
    )


class DeclarativeAssistant(SimpleAssistant):
    """
    Declarative way to create an assistant.
    Class docstring is used as the prompt; methods are used as functions.

    Example:

        class Mathematician(SimpleAssistant):
            "You are a mathematician. You can answer questions about math."

            def add_two_numbers(self, a: int, b: int) -> int:
                return a + b
    """

    def __init__(self):
        name = self.__class__.__name__
        system_prompt = self.__doc__ or ""
        functions = [getattr(self, name) for name, func in self.__class__.__dict__.items() if callable(func)]
        toolkit = FunctionToolkit(functions)
        super().__init__(name=name, system_prompt=system_prompt, toolkit=toolkit)


if __name__ == "__main__":

    class Mathematician(DeclarativeAssistant):
        """
        You are a mathematician. You are good at math. You can answer questions about math.
        """

        def add_two_numbers(self, a: int, b: int) -> int:
            """
            Add two numbers

            Args:
              a (int): The first number
              b (int): The second number

            Returns:
              int: The sum of the two numbers
            """
            return a + b

    chat = Chat(state=ChatState.create_new("id", "assistant"))
    chat.state.messages.append({"id": "1", "role": "user", "name": "user", "content": "What is three plus one?"})

    mathematician = Mathematician()
    message = mathematician.run(chat)

    print("Response:", message)
