import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from typing import Literal, NotRequired, Optional, TypedDict

from fastapi import Request
from openai import AsyncOpenAI
from pydantic import BaseModel
from starlette.requests import ClientDisconnect

MessageCategory = Literal["info", "success", "warning", "error"]


class Message(TypedDict):
    """Messages that are inside a chat."""

    id: str
    role: Literal["user", "assistant"]
    name: str
    content: str
    # Messages with category are for displaying special messages to the user.
    # They should not be sent to the completion API.
    # They get filtered out from Chat.state.messages list provided to the Assistant.run().
    category: NotRequired[Optional[MessageCategory]]


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

    def __init__(self, state: ChatState):
        # State is the chat that is persisted to disk.
        self.state = state

        # Message that are put here will be sent over SSE by the web server.
        self._queue = asyncio.Queue()

        # These will be set by the request handler before passing the Chat to the Assistant.run().
        self._request: Optional[Request] = None
        self._assistant: Optional[Assistant] = None

    # TODO implement Chat.add_image method
    async def add_image(self): ...

    async def add_message(self, content: str, category: Optional[MessageCategory] = None):
        assert isinstance(self._assistant, Assistant)
        message = Message(
            id=str(uuid.uuid4()),
            role="assistant",
            name=self._assistant.name,
            content=content,
            category=category,
        )
        return await self._add_message(message)

    async def _add_message(self, message: Message):
        await self.begin_message(message.get("category"))
        await self.add_chunk(message["content"])
        await self.end_message()

    async def begin_message(self, category: Optional[MessageCategory] = None):
        self._message_id = str(uuid.uuid4())
        self._chunks = []
        self._message_category: Optional[MessageCategory] = category
        assert isinstance(self._assistant, Assistant)
        await self._queue_message(
            {
                "type": "begin_message",
                "id": self._message_id,
                "name": self._assistant.name,
                "category": category,
            }
        )

    async def add_chunk(self, chunk: str):
        self._chunks.append(chunk)
        await self._queue_message({"type": "add_chunk", "chunk": chunk})

    async def end_message(self):
        assert isinstance(self._assistant, Assistant)
        content = "".join(self._chunks)
        message = Message(
            id=self._message_id,
            role="assistant",
            name=self._assistant.name,
            content=content,
            category=self._message_category,
        )
        self.state.messages.append(message)
        await self._queue_message({"type": "end_message", "id": self._message_id})

    async def _queue_message(self, message: dict):
        if not isinstance(self._request, Request):
            return
        if await self._request.is_disconnected():
            raise ClientDisconnect
        await self._queue.put(message)

    async def _update_title(self):
        class TitleResponse(BaseModel):
            title: str

        instructions = """
            You are a helpful summarizer.
            Your input is the first 2 messages of a conversation.
            Output a title for the conversation.
        """
        input = (
            f"<user>{self.state.messages[0]['content']}</user>\n\n"
            f"<assistant>{self.state.messages[1]['content']}</assistant>"
        )
        client = AsyncOpenAI()
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            response_format=TitleResponse,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": input},
            ],
        )
        instance = response.choices[0].message.parsed
        assert isinstance(instance, TitleResponse)
        self.state.title = instance.title
        await self._queue_message({"type": "update_title", "title": self.state.title})


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
