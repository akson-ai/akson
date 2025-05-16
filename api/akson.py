"""
akson package contains the interface that needs to be implemented by assistants.
"""

import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from typing import Literal, Optional

from fastapi import Request
from litellm import ChatCompletionMessageToolCall as LitellmToolCall
from litellm import Message as LitellmMessage
from litellm.types.utils import Function
from pydantic import BaseModel
from starlette.requests import ClientDisconnect


class ToolCall(BaseModel):
    id: str
    name: str  # Function name
    arguments: str  # Serialized JSON

    @classmethod
    def from_litellm(cls, tool_call: LitellmToolCall):
        return cls(
            id=tool_call.id,
            name=tool_call.function.name or "",
            arguments=tool_call.function.arguments,
        )

    def to_litellm(self):
        return LitellmToolCall(
            id=self.id,
            function=Function(name=self.name, arguments=self.arguments),
        )


class Message(BaseModel):
    id: str
    role: Literal["user", "assistant", "tool"]
    name: str  # Name of the assistant
    content: str
    tool_calls: Optional[list[ToolCall]] = None  # Only set if role is "assistant"
    tool_call_id: Optional[str] = None  # Only set if role is "tool"

    @classmethod
    def from_litellm(cls, message: LitellmMessage, *, name: str):
        return cls(
            id=str(uuid.uuid4()),
            role=message.role,  # type: ignore
            name=name,
            content=message.content or "",
            tool_calls=[ToolCall.from_litellm(tool_call) for tool_call in message.tool_calls or []] or None,
            tool_call_id=message.get("tool_call_id"),
        )

    def to_litellm(self):
        return LitellmMessage(
            id=self.id,
            role=self.role,  # type: ignore
            name=self.name,
            content=self.content,
            tool_calls=[tool_call.to_litellm() for tool_call in self.tool_calls or []],
            tool_call_id=self.tool_call_id,
        )


class ChatState(BaseModel):
    """Chat that can be saved and loaded from a file."""

    id: str
    messages: list[Message]
    assistant: Optional[str] = None
    title: Optional[str] = None

    @classmethod
    def create_new(cls, id: str, assistant: str):
        return cls(
            id=id,
            assistant=assistant,
            messages=[],
        )

    @classmethod
    def load_from_disk(cls, chat_id: str):
        with open(cls.file_path(chat_id), "r") as f:
            content = f.read()
            return cls.model_validate_json(content)

    def save_to_disk(self):
        os.makedirs("chats", exist_ok=True)
        with open(self.file_path(self.id), "w") as f:
            f.write(self.model_dump_json(indent=2))

    @staticmethod
    def file_path(id: str):
        return os.path.join("chats", f"{id}.json")


class Chat:
    """
    Chat holds state and handles sending and receiving messages.
    It is passed to the assistant's run method.
    This serves as the main interface between the assistant and the web application.
    """

    def __init__(self, *, state: ChatState):
        # Holds the chat's persistent state loaded from disk.
        # Mainly includes the history of chat messages, which is a list of litellm.Message.
        self.state = state
        """Holds the chat's persistent state loaded from disk."""

        # Message that are put here will be sent over SSE by the web server.
        self._queue: Optional[asyncio.Queue] = None

        # HTTP request
        self._request: Optional[Request] = None

        # These will be set by the Assistant.run() method.
        self._structured_output: Optional[BaseModel] = None

    @classmethod
    def temp(cls):
        state = ChatState(id="", messages=[], assistant="", title="")
        return cls(state=state)

    async def begin_message(
        self,
        role: Literal["assistant", "tool"],
        category: Optional[Literal["info", "success", "warning", "error"]] = None,
    ) -> str:
        # Generate a unique message ID.
        # This ID is used to identify the message when client wants to delete it.
        message_id = str(uuid.uuid4())

        await self._queue_message(
            {
                "type": "begin_message",
                "id": message_id,
                "role": role,
                "name": self.state.assistant,
                "category": category,
            }
        )
        return message_id

    async def add_chunk(self, location: Literal["content", "function_name", "function_arguments"], chunk: str):
        await self._queue_message(
            {
                "type": "add_chunk",
                "location": location,
                "chunk": chunk,
            }
        )

    async def end_message(self):
        await self._queue_message({"type": "end_message"})

    async def set_structured_output(self, output: BaseModel):
        self._structured_output = output

    async def _queue_message(self, message: dict):
        if self._request and await self._request.is_disconnected():
            raise ClientDisconnect
        if self._queue:
            await self._queue.put(message)


class Assistant(ABC):
    """Assistants are used to generate responses to chats."""

    def __repr__(self):
        return f"Assistant<{self.name}>"

    @property
    def name(self) -> str:
        """
        Name of the assistant. Visible in the UI.
        """
        return self.__class__.__name__

    # TODO add description method to Assistant

    @abstractmethod
    async def run(self, chat: Chat) -> None:
        """
        Run the assistant on the given chat.
        This method will be called by the web server.
        """
        ...
