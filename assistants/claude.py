import os

import anthropic
from anthropic.types import (
    MessageParam,
    RawContentBlockDeltaEvent,
    RawContentBlockStopEvent,
    TextBlock,
    TextDelta,
)

from framework import Assistant, Chat
from logger import logger


class Claude(Assistant):
    """Assistant that uses Anthropic's Claude API to generate responses."""

    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def run(self, chat: Chat) -> None:
        logger.debug(f"Completing chat with Claude...\nLast message: {chat.state.messages[-1]}")

        # Convert chat messages to Anthropic format
        messages = self._get_anthropic_messages(chat)

        # Stream the response
        await self._stream_response(messages, chat)

    def _get_anthropic_messages(self, chat: Chat) -> list[MessageParam]:
        messages: list[MessageParam] = []

        # Convert chat messages to Anthropic format
        for message in chat.state.messages:
            if message.get("category"):
                continue
            if message["role"] == "user":
                messages.append({"role": "user", "content": message["content"]})
            elif message["role"] == "assistant":
                messages.append({"role": "assistant", "content": message["content"]})

        return messages

    async def _stream_response(self, messages: list[MessageParam], chat: Chat) -> None:
        await chat.begin_message()
        async with self._client.messages.stream(
            model=os.environ["ANTHROPIC_MODEL"],
            messages=messages,
            max_tokens=4096,
        ) as stream:
            async for chunk in stream:
                match chunk:
                    case RawContentBlockDeltaEvent(delta=TextDelta()):
                        assert isinstance(chunk.delta, TextDelta)
                        await chat.add_chunk(chunk.delta.text)
                    case RawContentBlockStopEvent(content_block=TextBlock()):
                        await chat.end_message()


claude = Claude()
