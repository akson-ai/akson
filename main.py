import json
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

from framework import Assistant, Chat, ChatState, Message
from loader import load_assistants
from logger import logger

# TODO save tool calls as openai format in messages
# TODO write an email assistant
# TODO write news assistant
# TODO think about how to convert assistants to agents
# TODO add more use case items
# TODO add stateful agent

load_dotenv()

# Ensure chats directory exists
os.makedirs("chats", exist_ok=True)

assistants = {assistant.name: assistant for assistant in load_assistants().values()}

default_assistant = os.getenv("DEFAULT_ASSISTANT", "ChatGPT")

# Need to keep a single instance of each chat in memory in order to do pub/sub on queue
# TODO try streaming response
chats: dict[str, Chat] = {}


def _get_chat_state(chat_id: str) -> ChatState:
    try:
        return ChatState.load_from_disk(chat_id)
    except FileNotFoundError:
        return ChatState.create_new(chat_id, default_assistant)


def _get_chat(chat_id: str) -> Chat:
    try:
        return chats[chat_id]
    except KeyError:
        state = _get_chat_state(chat_id)
        chat = Chat(state)
        chats[chat_id] = chat
        return chat


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AssistantModel(BaseModel):
    name: str

    class Config:
        title = "Assistant"


@app.get("/assistants", response_model=list[AssistantModel])
async def get_assistants():
    """Return a list of available assistants."""
    return [AssistantModel(name=assistant.name) for assistant in sorted(assistants.values(), key=lambda a: a.name)]


class ChatSummary(BaseModel):
    id: str
    title: str
    last_updated: datetime


@app.get("/chats", response_model=list[ChatSummary])
async def get_chats():
    """Return a list of all chat sessions."""
    chat_files = []
    for filename in os.listdir("chats"):
        if filename.endswith(".json"):
            chat_id = filename[:-5]  # Remove .json extension
            try:
                state = ChatState.load_from_disk(chat_id)

                # Get the last modified time of the file
                last_updated = os.path.getmtime(ChatState.file_path(chat_id))

                chat_files.append(
                    ChatSummary(
                        id=chat_id,
                        title=state.title or "Untitled Chat",
                        last_updated=datetime.fromtimestamp(last_updated),
                    )
                )
            except Exception as e:
                logger.error(f"Error loading chat {chat_id}: {e}")

    # Sort by last updated, newest first
    chat_files.sort(key=lambda x: x.last_updated, reverse=True)
    return chat_files


@app.get("/{chat_id}/state", response_model=ChatState)
async def get_chat_state(state: ChatState = Depends(_get_chat_state)):
    """Return the state of a chat session."""
    return state


@app.put("/{chat_id}/assistant")
async def set_assistant(assistant: str = Body(...), chat: Chat = Depends(_get_chat)):
    """Update the assistant for a chat session."""
    chat.state.assistant = assistant
    chat.state.save_to_disk()


class MessageRequest(BaseModel):
    content: str = Body(...)
    assistant: str = Body(...)
    id: str = Body(...)


def _get_assistant(message: MessageRequest) -> Assistant:
    return assistants[message.assistant]


@app.post("/{chat_id}/message")
async def send_message(
    request: Request,
    message: MessageRequest,
    assistant: Assistant = Depends(_get_assistant),
    chat: Chat = Depends(_get_chat),
):
    """Handle a message from the client."""
    chat._request = request
    chat._assistant = assistant
    try:
        if message.content.strip() == "/clear":
            chat.state.messages.clear()
            chat.state.save_to_disk()
            logger.info("Chat cleared")
            await chat._queue_message({"type": "clear"})
            return

        user_message = Message(
            id=message.id,
            role="user",
            name="You",
            content=message.content,
        )
        chat.state.messages.append(user_message)

        await assistant.run(chat)

        # TODO update chat title async
        print(len(chat.state.messages))
        if len(chat.state.messages) == 2:
            await chat._update_title()
    except ClientDisconnect:
        # TODO save interrupted messages
        logger.info("Client disconnected")
    finally:
        chat._request = None
        chat._assistant = None
        chat.state.save_to_disk()


@app.delete("/{chat_id}/message/{message_id}")
async def delete_message(
    message_id: str,
    chat: Chat = Depends(_get_chat),
):
    """Delete a message by its ID."""
    chat.state.messages = [msg for msg in chat.state.messages if msg.get("id") != message_id]
    chat.state.save_to_disk()


@app.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat by its ID."""
    # Remove from memory if it exists
    if chat_id in chats:
        del chats[chat_id]

    # Remove the file from disk
    file_path = ChatState.file_path(chat_id)
    if os.path.exists(file_path):
        os.remove(file_path)


@app.get("/{chat_id}/events")
async def get_events(chat: Chat = Depends(_get_chat)):
    """Stream events to the client over SSE."""

    async def generate_events():
        while True:
            message = await chat._queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())
