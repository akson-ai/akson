"""
This module contains the Runner class, which is responsible for running an assistant on a chat.
"""

from langfuse.decorators import langfuse_context, observe

from akson import Assistant, Chat, Message


class Runner:
    def __init__(self, assistant: Assistant, chat: Chat | None = None):
        self.assistant = assistant
        if not chat:
            chat = Chat()
        self.chat = chat

    @observe()
    async def run(self, user_message: Message | str | None = None) -> list[Message]:
        langfuse_context.update_current_trace(
            name=self.assistant.name,
            session_id=self.chat.state.id,
        )
        if isinstance(user_message, str):
            user_message = Message(role="user", content=user_message)

        if user_message:
            self.chat.state.messages.append(user_message)

        await self.assistant.run(self.chat)
        return self.chat.new_messages
