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

from framework import Assistant, Chat, ChatState
from function_calling import FunctionToolkit, Toolkit
from logger import logger


class SimpleAssistant(Assistant):
    """Simple assistant that uses OpenAI's chat API to generate responses."""

    def __init__(self, name: str, system_prompt: str, toolkit: Optional[Toolkit] = None):
        self.system_prompt = system_prompt
        self._name = name
        self._client = AsyncOpenAI()
        self._toolkit = toolkit

    @property
    def name(self) -> str:
        return self._name

    async def run(self, chat: Chat) -> None:
        logger.debug(f"Completing chat...\nLast message: {chat.state.messages[-1]}")

        # These messages are sent to OpenAI in chat completion request.
        # Here, we convert chat messages in web UI to OpenAI format.
        messages = self._get_openai_messages(chat)

        message = await self._complete(messages, chat)
        messages.append(_convert_assistant_message(message))

        # We keep continue hitting OpenAI API until there are no more tool calls.
        if self._toolkit:
            while message.tool_calls:
                tool_calls = await self._toolkit.handle_tool_calls(message.tool_calls)
                messages.extend(tool_calls)

                message = await self._complete(messages, chat)
                messages.append(_convert_assistant_message(message))

    def _get_openai_messages(self, chat: Chat) -> list[ChatCompletionMessageParam]:
        messages: Sequence[ChatCompletionMessageParam] = []
        messages.append(ChatCompletionSystemMessageParam(role="system", content=self._get_system_prompt()))
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

        async with self._client.beta.chat.completions.stream(
            model=os.environ["OPENAI_MODEL"],
            messages=messages,
            **await self._tool_kwargs(),
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
                        if choice.finish_reason in ("stop", "tool_calls"):
                            return choice.message
                        raise NotImplementedError(f"finish_reason={choice.finish_reason}")

        raise Exception("Stream ended unexpectedly")

    async def _tool_kwargs(self) -> dict[str, Any]:
        if not self._toolkit:
            return {}
        tools = await self._toolkit.get_tools()
        if not tools:
            return {}
        return {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}


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
        super().__init__(name, system_prompt, toolkit)


# TODO put back StructuredOutput as assistants
# class StructuredOutput:
#     """Get structured output from a chat model."""

#     def __init__(self, system_prompt: str, response_format: type[BaseModel]):
#         self.system_prompt = system_prompt
#         self.response_format = response_format
#         self._chat = Chat()
#         self._client = AzureOpenAI()

#     def add_example(self, user_message: str, response: BaseModel):
#         """Add an example to the prompt."""
#         self._chat.messages.extend(
#             [
#                 {"role": "system", "name": "example_user", "content": user_message},
#                 {"role": "system", "name": "example_assistant", "content": response.model_dump_json()},
#             ]
#         )

#     def run(self, chat: Chat) -> object:
#         """Run the system prompt on chat and return the parsed response."""
#         response = self._client.beta.chat.completions.parse(
#             model=os.environ["OPENAI_MODEL"],
#             response_format=self.response_format,
#             messages=self._chat.messages + chat.messages,
#         )
#         instance = response.choices[0].message.parsed
#         assert isinstance(instance, self.response_format)
#         return instance

#     def run_user_message(self, user_message: str) -> object:
#         """Run the system prompt on a user message and return the parsed response."""
#         chat = Chat()
#         chat.messages.append({"role": "user", "content": user_message})
#         return self.run(chat)


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
