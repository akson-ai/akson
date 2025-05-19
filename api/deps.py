import os

from fastapi import Depends

import models
from akson import Assistant, Chat, ChatState
from pubsub import PubSub
from registry import Registry

# Load environment variables
default_assistant = os.getenv("DEFAULT_ASSISTANT", "ChatGPT")

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
        return ChatState.create_new(chat_id, default_assistant)


def get_chat(chat_id: str) -> Chat:
    return Chat(state=get_chat_state(chat_id), publisher=pubsub.get_publisher(chat_id))


def get_assistant(message: models.SendMessageRequest, chat: Chat = Depends(get_chat)) -> Assistant:
    assistant = chat.state.assistant
    if message.assistant:
        assistant = message.assistant
    if not assistant:
        assistant = default_assistant
    return registry.get_assistant(assistant)
