import asyncio
import json
import os
import traceback
from datetime import datetime

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Body, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

from akson import Assistant, Chat, ChatState, Message
from framework import Agent
from loader import load_objects
from logger import logger

load_dotenv()

# Ensure chats directory exists
os.makedirs("chats", exist_ok=True)

assistants = {}
for assistant in load_objects(Assistant, "assistants"):
    if assistant.name in assistants:
        raise Exception(f"Duplicate assistant found for {assistant.name}")
    else:
        assistants[assistant.name] = assistant

default_assistant = os.getenv("DEFAULT_ASSISTANT", "ChatGPT")
allow_origins = [origin.strip() for origin in os.getenv("ALLOW_ORIGINS", "*").split(",")]

# Need to keep a single instance of each chat in memory in order to do pub/sub on queue
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
        chat = Chat(state=state)
        chats[chat_id] = chat
        return chat


app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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


@app.post("/{chat_id}/message", response_model=list[Message])
async def send_message(
    request: Request,
    message: MessageRequest,
    background_tasks: BackgroundTasks,
    assistant: Assistant = Depends(_get_assistant),
    chat: Chat = Depends(_get_chat),
):
    """Handle a message from the client."""
    chat._request = request
    try:
        if message.content.strip() == "/clear":
            chat.state.messages.clear()
            chat.state.save_to_disk()
            logger.info("Chat cleared")
            await chat._queue_message({"type": "clear"})
            return []

        user_message = Message(
            id=message.id,
            role="user",  # type: ignore
            content=message.content,
        )
        chat.state.messages.append(user_message)

        await assistant.run(chat)
        background_tasks.add_task(update_title, chat)
    except ClientDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        traceback.print_exc()
        reply = await chat.reply("assistant")
        await reply.add_chunk(f"```{e.__class__.__name__}: {e}```")
        # TODO add category "error"
        await reply.end()
    finally:
        chat._request = None
        chat.state.save_to_disk()

    new_messages = chat.new_messages
    chat.new_messages = []
    return new_messages


async def update_title(self: Chat):
    if self.state.title:
        return

    class TitleResponse(BaseModel):
        title: str

    instructions = """
        You are a helpful summarizer.
        Your input is the first 2 messages of a conversation.
        Output a title for the conversation.
    """
    input = (
        f"<user>{self.state.messages[0].content}</user>\n\n" f"<assistant>{self.state.messages[1].content}</assistant>"
    )
    titler = Agent(name="Titler", model="gpt-4.1-nano", system_prompt=instructions, output_type=TitleResponse)
    response = await titler.respond(input)
    assert isinstance(response, TitleResponse)
    self.state.title = response.title
    await self._queue_message({"type": "update_title", "title": self.state.title})
    # TODO Fix race condition
    self.state.save_to_disk()


@app.delete("/{chat_id}/message/{message_id}")
async def delete_message(
    message_id: str,
    chat: Chat = Depends(_get_chat),
):
    """Delete a message by its ID."""
    chat.state.messages = [msg for msg in chat.state.messages if msg.id != message_id]
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
        chat._queue = asyncio.Queue()
        try:
            while True:
                message = await chat._queue.get()
                yield ServerSentEvent(json.dumps(message))
        finally:
            chat._queue = None

    return EventSourceResponse(generate_events())
