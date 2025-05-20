from pydantic import BaseModel

from akson import Chat
from framework import Agent


async def update_title(chat: Chat):
    if chat.state.title:
        return

    class TitleResponse(BaseModel):
        title: str

    instructions = """
        You are a helpful summarizer.
        Your input is the first 2 messages of a conversation.
        Output a title for the conversation.
    """
    input = (
        f"<user>{chat.state.messages[0].content}</user>\n\n" f"<assistant>{chat.state.messages[1].content}</assistant>"
    )
    titler = Agent(name="Titler", model="gpt-4.1-nano", system_prompt=instructions, output_type=TitleResponse)
    response = await titler.respond(input)
    assert isinstance(response, TitleResponse)
    chat.state.title = response.title
    await chat._queue_message({"type": "update_title", "title": chat.state.title})
    # TODO Fix race condition
    chat.state.save_to_disk()
