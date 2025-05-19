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

app = FastAPI()

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


@app.get("/{chat_id}/state", response_model=ChatState)
async def get_chat_state_endpoint(state: ChatState = Depends(deps.get_chat_state)):
    """Return the state of a chat session."""
    return state


@app.put("/{chat_id}/assistant")
async def set_assistant(assistant: str = Body(...), state: ChatState = Depends(deps.get_chat_state)):
    """Update the assistant for a chat session."""
    state.assistant = assistant
    state.save_to_disk()


@app.post("/{chat_id}/message", response_model=list[Message])
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

        chat.state.messages.append(
            Message(
                id=message.id,
                role="user",
                content=message.content,
            )
        )
        await assistant.run(chat)

        background_tasks.add_task(tasks.update_title, chat)
    except ClientDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        traceback.print_exc()
        reply = await chat.reply("assistant", name="Error")
        await reply.add_chunk(f"```{e.__class__.__name__}: {e}```")
        # TODO add category "error"
        await reply.end()
    finally:
        chat.state.save_to_disk()

    new_messages = chat.new_messages
    chat.new_messages = []
    return new_messages


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


@app.delete("/{chat_id}/message/{message_id}")
async def delete_message(
    message_id: str,
    state: ChatState = Depends(deps.get_chat_state),
):
    """Delete a message by its ID."""
    state.messages = [msg for msg in state.messages if msg.id != message_id]
    state.save_to_disk()


@app.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat by its ID."""
    file_path = ChatState.file_path(chat_id)
    if os.path.exists(file_path):
        os.remove(file_path)


@app.get("/{chat_id}/events")
async def get_events(chat_id: str, pubsub: PubSub = Depends(deps.get_pubsub)):
    """Stream events to the client over SSE."""

    async def generate_events():
        async with pubsub.subscribe(chat_id) as queue:
            while True:
                message = await queue.get()
                yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())
