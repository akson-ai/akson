import asyncio
import os
import uuid
from pathlib import Path

import click
from akson_client import AksonClient
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout


async def stream_events(client: AksonClient, chat_id: str):
    async for data in client.stream_events(chat_id):
        match data:
            case {"type": "begin_message"}:
                print("\nAssistant: ", end="", flush=True)
            case {"type": "add_chunk"}:
                print(data["chunk"], end="", flush=True)
            case {"type": "end_message"}:
                print("\n")


async def chat_loop(client: AksonClient, chat_id: str, assistant: str):
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
                    assistants = await client.get_assistants()
                    print(f"Available assistants: {', '.join(assistants)}\n")
                elif command == "/assistant":
                    if args:
                        await client.set_assistant(chat_id, args[0])
                        assistant = args[0]
                    print(f"Selected assistant: {assistant}\n")
                else:
                    print("Unknown command\n")

                continue

            await client.send_message(chat_id, user_input, assistant)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            continue


async def chat(chat_id: str, client: AksonClient):
    # Get chat state
    chat_state = await client.get_chat_state(chat_id)
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

    client = AksonClient(base_url)
    await chat(chat_id, client)


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
