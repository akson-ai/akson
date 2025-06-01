from langfuse.decorators import langfuse_context, observe

from akson import Assistant, Chat, Message


class Runner:

    def __init__(self, assistant: Assistant, chat: Chat | None = None):
        self.assistant = assistant
        if not chat:
            chat = Chat()
        self.chat = chat

    @observe()
    async def run(self, user_message: Message | str) -> list[Message]:
        if isinstance(user_message, str):
            user_message = Message(role="user", content=user_message)
        langfuse_context.update_current_trace(
            name=self.assistant.name,
            session_id=self.chat.state.id,
        )
        self.chat.state.messages.append(user_message)
        await self.assistant.run(self.chat)
        return self.chat.new_messages
