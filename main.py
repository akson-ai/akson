import json
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

from framework import Assistant, Chat, ChatState, Message
from loader import load_assistants
from logger import logger

# TODO write an email assistant
# TODO think about how to convert assistants to agents
# TODO add Replier assistant
# TODO add Rewriter assistant
# TODO add more use case items

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


@app.get("/", include_in_schema=False)
async def index():
    """Redirect to the chat app."""
    return RedirectResponse(f"/chat")


@app.get("/chat", include_in_schema=False)
async def get_chat_app(id: str | None = None):
    """Serve the chat web app."""
    if not id:
        return RedirectResponse(f"/chat?id={uuid.uuid4()}")
    return FileResponse("web/chat.html")


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
                # Get the first few characters of the first message as the title
                title = "Untitled Chat"
                if state.messages and len(state.messages) > 0:
                    first_message = state.messages[0]
                    if first_message["role"] == "user" and first_message["content"]:
                        title = first_message["content"][:30] + ("..." if len(first_message["content"]) > 30 else "")

                # Get the last modified time of the file
                last_updated = os.path.getmtime(ChatState.file_path(chat_id))

                chat_files.append(
                    ChatSummary(
                        id=chat_id,
                        title=title,
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

        user_message = Message(role="user", name="You", content=message.content)
        chat.state.messages.append(user_message)

        await assistant.run(chat)
    except ClientDisconnect:
        # TODO save interrupted messages
        logger.info("Client disconnected")
    finally:
        chat._request = None
        chat._assistant = None
        chat.state.save_to_disk()


@app.get("/{chat_id}/events")
async def get_events(chat: Chat = Depends(_get_chat)):
    """Stream events to the client over SSE."""

    async def generate_events():
        while True:
            message = await chat._queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())


# Must be mounted after above handlers
app.mount("/", StaticFiles(directory="web/static"))
