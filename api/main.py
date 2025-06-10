"""This module contains the FastAPI app."""

import json
import os
import traceback
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import rich
from fastapi import BackgroundTasks, Body, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

import deps
import models
import tasks
from akson import Assistant, Chat, ChatState, Message
from logger import logger
from pubsub import PubSub
from registry import UnknownAssistant
from runner import Runner

app = FastAPI(title="Akson API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOW_ORIGINS", "*").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    rich.print(exc.errors())
    return JSONResponse(str(exc), status_code=422)


@app.exception_handler(UnknownAssistant)
async def unknown_assistant_exception_handler(_: Request, exc: UnknownAssistant):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}


@app.get("/assistants", response_model=list[models.Assistant])
async def get_assistants():
    """Return a list of available assistants."""
    return [models.Assistant(name=assistant.name) for assistant in deps.registry.assistants]


@app.get("/chats", response_model=list[models.ChatSummary])
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
                    models.ChatSummary(
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


@app.get("/chats/{chat_id}", response_model=ChatState)
async def get_chat_state_endpoint(state: ChatState = Depends(deps.get_chat_state)):
    """Return the state of a chat session."""
    return state


@app.put("/chats/{chat_id}/assistant")
async def set_assistant(assistant: str = Body(...), state: ChatState = Depends(deps.get_chat_state)):
    """Update the assistant for a chat session."""
    state.assistant = assistant
    state.save_to_disk()


@app.post("/chats/{chat_id}/messages", response_model=list[Message])
async def send_message(
    message: models.SendMessageRequest,
    background_tasks: BackgroundTasks,
    assistant: Assistant = Depends(deps.get_assistant),
    chat: Chat = Depends(deps.get_chat),
):
    """Handle a message from the client."""
    try:
        if message.content.startswith("/"):
            return await handle_command(chat, message.content)
        user_message = Message(
            id=message.id,
            role="user",
            content=message.content,
        )
        assistant_messages = await Runner(assistant, chat).run(user_message)
        background_tasks.add_task(tasks.update_title, chat)
        return assistant_messages
    except ClientDisconnect:
        logger.info("Client disconnected")
        return []
    except Exception as e:
        await _handle_exception(chat, e)
        raise
    finally:
        chat.state.save_to_disk()


async def _handle_exception(chat: Chat, e: Exception):
    logger.error(f"Error handling message: {e}")
    traceback.print_exc()

    tb = e.__traceback__
    extracted_tb = traceback.extract_tb(tb)
    filename, lineno, func, text = extracted_tb[-1]  # The last call is usually your code line
    if isinstance(e, AssertionError):
        text = f"```py\n{text}\n```"
    else:
        text = f"```\n{e}\n```"
    content = f"`{e.__class__.__name__} at {filename}:{lineno} in {func}`:\n{text}"

    # TODO add category "error"
    reply = await chat.reply("assistant", name="Error")
    await reply.add_chunk(content)
    await reply.end()


async def handle_command(chat: Chat, content: str):
    command, *args = content.split()
    match command:
        case "/clear":
            chat.state.messages.clear()
            logger.info("Chat cleared")
            await chat._queue_message({"type": "clear"})
            return [Message(role="assistant", content="Chat cleared")]
        case "/assistant":
            if len(args) != 1:
                raise Exception("Usage: /assistant <name>")
            assistant = deps.registry.get_assistant(args[0])
            chat.state.assistant = assistant.name
            await chat._queue_message({"type": "update_assistant", "assistant": chat.state.assistant})
            return [Message(role="assistant", content=f"Assistant set to {assistant.name}")]
        case _:
            raise Exception("Unknown command")


@app.delete("/chats/{chat_id}/messages/{message_id}")
async def delete_message(
    message_id: str,
    state: ChatState = Depends(deps.get_chat_state),
):
    """Delete a message by its ID."""
    state.messages = [msg for msg in state.messages if msg.id != message_id]
    state.save_to_disk()


@app.post("/chats/{chat_id}/messages/{message_id}/retry", response_model=list[Message])
async def retry_message(message_id: str, chat: Chat = Depends(deps.get_chat)):
    """Retry from a message by removing it and all subsequent messages, then rerun the assistant."""
    try:
        try:
            message_index = [msg.id for msg in chat.state.messages].index(message_id)
        except ValueError:
            return JSONResponse(status_code=404, content={"detail": "Message not found"})

        retry_message = chat.state.messages[message_index]
        assert retry_message.role == "assistant"
        assert retry_message.name
        assistant = deps.registry.get_assistant(retry_message.name)
        chat.state.messages = chat.state.messages[:message_index]
        assistant_messages = await Runner(assistant, chat).run()
        return assistant_messages
    except ClientDisconnect:
        logger.info("Client disconnected")
        return []
    except Exception as e:
        await _handle_exception(chat, e)
        raise
    finally:
        chat.state.save_to_disk()


@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat by its ID."""
    file_path = ChatState.file_path(chat_id)
    if os.path.exists(file_path):
        os.remove(file_path)


@app.get("/chats/{chat_id}/events")
async def get_events(chat_id: str, pubsub: PubSub = Depends(deps.get_pubsub)):
    """Stream events to the client over SSE."""

    async def generate_events():
        async with pubsub.subscribe(chat_id) as queue:
            while True:
                message = await queue.get()
                yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())
