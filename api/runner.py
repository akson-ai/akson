"""
This module contains the Runner class, which is responsible for running an assistant on a chat.
"""

from enum import StrEnum
from typing import Optional

from langfuse.decorators import langfuse_context, observe
from pydantic import BaseModel, Field

from akson import Assistant, Chat, Message


class TaskStatus(StrEnum):
    WORKING = "WORKING"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskResponse(BaseModel):
    status: TaskStatus
    result: Optional[str] = Field(
        # default=None, description="Result of the task (if user wanted to see emails, contains emails)"
        default=None,
        description="Result of the task (e.g. the data requested by user)",
    )


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

    @observe()
    async def complete_task(self, task: str) -> TaskResponse:
        from framework import LLMAssistant

        user_message = Message(role="user", content=f"Complete the task: {task}")
        self.chat.state.messages.append(user_message)
        await self.assistant.run(self.chat)

        task_analyzer = LLMAssistant(
            name="TaskAnalyzer",
            model="gpt-4.1-nano",
            system_prompt="""
            Analyze the conversation and extract the task details and output.
            You must extract all details asked from the conversation because the user cannot see this conversation.
            For example if user is asking for email, you must extract the list of emails and output them.
            """,
            output_type=TaskResponse,
        )

        temp = Chat()
        temp.state.messages = self.chat.state.messages.copy()
        await task_analyzer.run(temp)

        output = temp.state.messages[-1].content
        return TaskResponse.model_validate_json(output)
