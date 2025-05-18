"""
akson package contains the interface that needs to be implemented by assistants.
"""

import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from typing import Literal, Optional

from fastapi import Request
from pydantic import BaseModel
from starlette.requests import ClientDisconnect


class ToolCall(BaseModel):
    id: str
    name: str  # Function name
    arguments: str  # Serialized JSON


class Message(BaseModel):
    id: str
    role: Literal["user", "assistant", "tool"]
    name: Optional[str] = None  # Name of the assistant
    content: str
    tool_call: Optional[ToolCall] = None  # Only set if role is "assistant"
    tool_call_id: Optional[str] = None  # Only set if role is "tool"


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


class Reply:

    def __init__(self, *, chat: "Chat", role: Literal["assistant", "tool"], name: str):
        self.chat = chat
        self.message = Message(
            id=str(uuid.uuid4()),
            role=role,
            name=name,
            content="",
        )

    # Need to have this method because constructors cannot be async
    @classmethod
    async def create(cls, *args, **kwargs) -> "Reply":
        self = cls(*args, **kwargs)
        await self.chat._queue_message(
            {
                "type": "begin_message",
                "id": self.message.id,
                "role": self.message.role,
                "name": self.message.name,
                # TODO send category on create reply
                # "category": category,
            }
        )
        return self

    FieldType = Literal["content", "tool_call.id", "tool_call.name", "tool_call.arguments", "tool_call_id"]

    async def add_chunk(self, chunk: str, *, field: FieldType = "content"):
        if field == "content":
            self.message.content += chunk
        elif field == "tool_call_id":
            self.message.tool_call_id = chunk
        elif field.startswith("tool_call."):
            if not self.message.tool_call:
                self.message.tool_call = ToolCall(id="", name="", arguments="")
            match field:
                case "tool_call.id":
                    self.message.tool_call.id = chunk
                case "tool_call.name":
                    self.message.tool_call.name += chunk
                case "tool_call.arguments":
                    self.message.tool_call.arguments += chunk
        await self.chat._queue_message(
            {
                "type": "add_chunk",
                "id": self.message.id,
                # TODO rename as field
                "location": field,
                "chunk": chunk,
            }
        )

    async def end(self):
        await self.chat._queue_message(
            {
                "type": "end_message",
                "id": self.message.id,
            }
        )
        self.chat.new_messages.append(self.message)
        self.chat.state.messages.append(self.message)
        self.chat.state.save_to_disk()


class Chat:
    """
    Chat holds state and handles sending and receiving messages.
    It is passed to the assistant's run method.
    This serves as the main interface between the assistant and the web application.
    """

    def __init__(self, *, state: ChatState):
        # Holds the chat's persistent state loaded from disk.
        # Mainly includes the history of chat messages, which is a list of Message.
        self.state = state
        """Holds the chat's persistent state loaded from disk."""

        # Message that are put here will be sent over SSE by the web server.
        self._queue: Optional[asyncio.Queue] = None

        # HTTP request
        self._request: Optional[Request] = None

        # These will be set by the Assistant.run() method.
        self._structured_output: Optional[BaseModel] = None

        # Contains new messages generated during the agent run.
        self.new_messages: list[Message] = []

    @classmethod
    def temp(cls):
        state = ChatState(id="", messages=[], assistant="", title="")
        return cls(state=state)

    async def reply(self, role: Literal["assistant", "tool"]) -> Reply:
        # category: Optional[Literal["info", "success", "warning", "error"]] = None,
        # TODO name could be coming from the request context
        return await Reply.create(chat=self, role=role, name=self.state.assistant)

    async def set_structured_output(self, output: BaseModel):
        self._structured_output = output

    async def _queue_message(self, message: dict):
        if self._request and await self._request.is_disconnected():
            raise ClientDisconnect
        if self._queue:
            await self._queue.put(message)


class Assistant(ABC):
    """Assistants are used to generate responses to chats."""

    def __init__(self):
        self.name: str = self.__class__.__name__
        """Name of the assistant. Visible in the UI."""
        self.description: Optional[str] = None
        """Description of the assistant, its purpose and capabilities."""

    def __repr__(self):
        return f"Assistant<{self.name}>"

    @abstractmethod
    async def run(self, chat: Chat) -> None:
        """
        Run the assistant on the given chat.
        This method will be called by the web server.
        """
        ...
