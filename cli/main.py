import asyncio
import json
import os
import uuid
from pathlib import Path

import click
import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout


async def get_assistants(client: httpx.AsyncClient) -> list[str]:
    response = await client.get(f"/assistants")
    response.raise_for_status()
    return [assistant["name"] for assistant in response.json()]


async def set_assistant(client: httpx.AsyncClient, chat_id: str, assistant: str) -> None:
    response = await client.put(
        f"/{chat_id}/assistant",
        headers={"Content-Type": "text/plain"},
        content=assistant.encode(),
    )
    response.raise_for_status()


async def get_chat_state(client: httpx.AsyncClient, chat_id: str) -> dict:
    response = await client.get(f"/{chat_id}/state")
    response.raise_for_status()
    return response.json()


async def send_message(client: httpx.AsyncClient, chat_id: str, content: str, assistant: str) -> None:
    response = await client.post(
        f"/{chat_id}/message",
        json={"content": content, "assistant": assistant, "id": str(uuid.uuid4())},
    )
    response.raise_for_status()


async def stream_events(client: httpx.AsyncClient, chat_id: str):
    async with client.stream("GET", f"/{chat_id}/events", timeout=None) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                match data:
                    case {"type": "begin_message"}:
                        print("\nAssistant: ", end="", flush=True)
                    case {"type": "add_chunk"}:
                        print(data["chunk"], end="", flush=True)
                    case {"type": "end_message"}:
                        print("\n")


async def chat_loop(client: httpx.AsyncClient, chat_id: str, assistant: str):
    session = PromptSession(history=FileHistory(Path.home() / ".akson_chat_history.txt"))
    while True:
        try:
            user_input = await session.prompt_async("You: ")

            user_input = user_input.strip()
            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                command, *args = user_input.split(" ")
                if command == "/assistants":
                    assistants = await get_assistants(client)
                    print(f"Available assistants: {', '.join(assistants)}\n")
                elif command == "/assistant":
                    if args:
                        await set_assistant(client, chat_id, args[0])
                        assistant = args[0]
                    print(f"Selected assistant: {assistant}\n")
                else:
                    print("Unknown command\n")

                continue

            await send_message(client, chat_id, user_input, assistant)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            continue


async def chat(chat_id: str, client: httpx.AsyncClient):
    # Get chat state
    chat_state = await get_chat_state(client, chat_id)
    assistant = chat_state["assistant"]

    # Print previous messages if they exist
    if "messages" in chat_state:
        for message in chat_state["messages"]:
            role = "Assistant" if message["role"] == "assistant" else "You"
            print(f"{role}: {message['content']}\n")

    # Patching stdout to make sure that the text appears above the prompt,
    # and that it doesn't destroy the output from the renderer.
    with patch_stdout():
        # Create tasks for both coroutines
        chat_task = asyncio.create_task(chat_loop(client, chat_id, assistant))
        stream_task = asyncio.create_task(stream_events(client, chat_id))

        # Wait for chat loop to complete
        try:
            await chat_task
        finally:
            # Cancel the stream task when chat loop ends
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass


async def main_async(chat_id: str | None, base_url: str):
    if not chat_id:
        chat_id = str(uuid.uuid4())
        print(f"Using new chat ID: {chat_id}\n")

    client = httpx.AsyncClient(base_url=base_url)
    try:
        await chat(chat_id, client)
    finally:
        await client.aclose()


@click.command()
@click.argument("chat_id", required=False)
@click.option(
    "--base-url", default=os.getenv("AKSON_API_BASE_URL", "http://localhost:8000"), help="API server base URL"
)
def main(chat_id: str | None, base_url: str):
    """Start the chat CLI

    CHAT_ID: Optional chat ID to connect to an existing chat. If not provided, a new UUID will be generated.
    """
    asyncio.run(main_async(chat_id, base_url))


if __name__ == "__main__":
    main()
