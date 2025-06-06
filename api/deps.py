import os

from fastapi import Depends, Request
from starlette.requests import ClientDisconnect

import models
from akson import Assistant, Chat, ChatState
from pubsub import PubSub
from registry import Registry, UnknownAssistant

# Load environment variables
DEFAULT_ASSISTANT = os.getenv("DEFAULT_ASSISTANT", "ChatGPT")

# Manages assistants
registry = Registry()

# For sending chat events to clients
pubsub = PubSub()

# Ensure chats directory exists
os.makedirs("chats", exist_ok=True)


def get_pubsub() -> PubSub:
    return pubsub


def get_chat_state(chat_id: str) -> ChatState:
    try:
        return ChatState.load_from_disk(chat_id)
    except FileNotFoundError:
        return ChatState.create_new(chat_id, _get_default_assistant().name)


def get_chat(chat_id: str, request: Request) -> Chat:
    async def publish(message):
        if await request.is_disconnected():
            raise ClientDisconnect
        return await pubsub.publish(chat_id, message)

    return Chat(state=get_chat_state(chat_id), publisher=publish)


def get_assistant(message: models.SendMessageRequest, chat: Chat = Depends(get_chat)) -> Assistant:
    assistant = chat.state.assistant
    if message.assistant:
        assistant = message.assistant
    if message.content.startswith("@"):
        assistant = message.content[1:].split()[0]
    if not assistant:
        assistant = _get_default_assistant().name
    return registry.get_assistant(assistant)


def _get_default_assistant() -> Assistant:
    try:
        return registry.get_assistant(DEFAULT_ASSISTANT)
    except UnknownAssistant:
        return registry.assistants[0]
