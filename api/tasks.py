"""This module contains the background tasks used by the FastAPI app."""

from pydantic import BaseModel

from akson import Assistant, Chat, ChatState
from framework import LLMAssistant


async def update_title(chat: Chat):
    if chat.state.title:
        return

    class TitleResponse(BaseModel):
        title: str

    titler: Assistant = LLMAssistant(
        name="Titler",
        model="gpt-4.1-nano",
        system_prompt="Analyze the conversation and output a title for the conversation.",
        output_type=TitleResponse,
    )

    temp = Chat()
    temp.state.messages = chat.state.messages.copy()

    await titler.run(temp)

    output = temp.state.messages[-1].content
    instance = TitleResponse.model_validate_json(output)

    # TODO Fix race condition. Lock?
    state = ChatState.load_from_disk(chat.state.id)
    state.title = instance.title
    state.save_to_disk()
    await chat._queue_message({"type": "update_title", "title": chat.state.title})
