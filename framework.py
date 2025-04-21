import os
import time
import uuid
from datetime import datetime
from io import StringIO

# from io import StringIO  # TODO use StringIO to accumulate message content and function arguments
from typing import Any, Optional

from litellm import CustomStreamWrapper, acompletion
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Function,
    Message,
)
from pydantic import BaseModel

from akson import Assistant, Chat
from function_calling import FunctionToolkit, Toolkit
from logger import logger


class SimpleAssistant(Assistant):
    """Simple assistant that uses OpenAI's chat API to generate responses."""

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
        logger.debug(f"Completing chat...\nLast message: {chat.state.messages[-1]}")

        # These messages are sent to the LLM API, prefixed by the system prompt.
        messages = self._get_messages(chat)

        message = await self._complete(messages, chat)
        messages.append(message)

        # We keep continue hitting OpenAI API until there are no more tool calls.
        current_turn = 0
        if self.toolkit:
            while message.tool_calls:
                current_turn += 1
                if current_turn > self.max_turns:
                    raise Exception(f"Max turns ({self.max_turns}) exceeded")

                tool_calls = await self.toolkit.handle_tool_calls(message.tool_calls)

                # All messages must have unique IDs
                for tool_call in tool_calls:
                    tool_call["id"] = str(uuid.uuid4())
                    tool_call["name"] = self.name

                messages.extend(tool_calls)
                chat.state.messages.extend(tool_calls)
                chat.state.save_to_disk()

                for tool_call in tool_calls:
                    await chat.begin_message("tool")
                    await chat.add_chunk(tool_call["content"], "content")

                message = await self._complete(messages, chat)
                messages.append(message)

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

    async def _complete(self, messages: list[Message], chat: Chat) -> Message:
        logger.info("Completing chat")
        for message in messages:
            # TODO handle assistant names
            # if "name" in message:
            #     message["name"] = re.sub(r"[^a-zA-Z0-9_-]", "_", message["name"])
            logger.debug(message)

        # TODO handle streaming of message; track state (which phase are we in?)
        # Because we're streaming, we need to track whether a message has started or not.
        # message_started = False

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
        await chat.begin_message("assistant")

        # We will aggregate delta messages and store them in these variables until we see a finish_reason.
        # This is the only way to get the full content of the message.
        # We'll return this value at the end of the function.
        message_role = None
        message_content = StringIO()
        tool_call_id = None
        function_name = StringIO()
        function_arguments = StringIO()

        async for chunk in response:
            assert chunk.__class__.__name__ == "ModelResponseStream"
            assert len(chunk.choices) == 1
            choice = chunk.choices[0]
            if choice.delta.tool_calls:
                if id := choice.delta.tool_calls[0].id:
                    tool_call_id = id
                if name := choice.delta.tool_calls[0].function.name:
                    function_name.write(name)
                    await chat.add_chunk(name, "function_name")
                if args := choice.delta.tool_calls[0].function.arguments:
                    function_arguments.write(args)
                    await chat.add_chunk(args, "function_arguments")
            if choice.delta.role:
                message_role = choice.delta.role
            if content := choice.delta.content:
                message_content.write(content)
                await chat.add_chunk(content, "content")

            if finish_reason := choice.finish_reason:
                message = Message(
                    id=str(uuid.uuid4()),
                    role=message_role,  # type: ignore
                    content=message_content.getvalue(),
                )
                if finish_reason == "stop":
                    if self.output_type:
                        instance = self.output_type.model_validate_json(message_content.getvalue())
                        await chat.set_structured_output(instance)
                elif finish_reason == "tool_calls":
                    message.tool_calls = [
                        ChatCompletionMessageToolCall(
                            id=tool_call_id,
                            function=Function(
                                name=function_name.getvalue(),
                                arguments=function_arguments.getvalue(),
                            ),
                        )
                    ]
                else:
                    raise NotImplementedError(f"finish_reason={finish_reason}")

                await chat.end_message()
                return message

            # await chat.begin_message(category="info")

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

    model = os.environ["DEFAULT_MODEL"]

    def __init__(self):
        name = self.__class__.__name__
        system_prompt = self.__doc__ or ""
        functions = [getattr(self, name) for name, func in self.__class__.__dict__.items() if callable(func)]
        toolkit = FunctionToolkit(functions)
        super().__init__(name=name, model=self.model, system_prompt=system_prompt, toolkit=toolkit)


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

    chat = Chat.temp()
    chat.state.messages.append(
        Message(
            id=str(uuid.uuid4()),
            role="user",  # type: ignore
            content="What is three plus one?",
        )
    )

    mathematician = Mathematician()
    message = mathematician.run(chat)

    print("Response:", message)
