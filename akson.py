import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from typing import Literal, Optional

from fastapi import Request
from litellm import Message
from pydantic import BaseModel
from starlette.requests import ClientDisconnect


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
        return self.__class__.__name__

    # TODO add description method to Assistant

    @abstractmethod
    async def run(self, chat: Chat) -> None: ...
