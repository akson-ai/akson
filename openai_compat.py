import time
import json
import random
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

from framework import Agent


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool | None = False
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


def chat_streaming_chunk(response: ChatCompletionResponse, content: str, *, finish_reason: str | None = None):
    return {
        "id": response.id,
        "object": "chat.completions.chunk",
        "created": response.created,
        "model": response.model,
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "delta": {"role": "assistant", "content": content},
            }
        ],
    }


def setup_routes(app: FastAPI, agents: dict[str, Agent]):
    async def chat_completions(request: ChatCompletionRequest):
        if request.model == "gpt-4o":
            request.model = "ChatGPT"
        try:
            agent = agents[request.model]
        except KeyError:
            raise HTTPException(status_code=404, detail="Agent not found")

        messages = _convert_messages(request.messages)
        content = agent.complete(messages)

        completion_tokens = len(content.split())
        prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)

        response = ChatCompletionResponse(
            id=f"chatcmpl-{random.randint(1000000, 9999999)}",
            object="chat.completion",
            created=int(time.time()),
            model=request.model,
            choices=[Choice(index=0, message=Message(role="assistant", content=content), finish_reason="stop")],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

        if not request.stream:
            return response

        async def generator():
            yield {"data": json.dumps(chat_streaming_chunk(response, ""))}

            # Fake streaming of whole content
            for word in content.split():
                yield {"data": json.dumps(chat_streaming_chunk(response, word + " "))}

            yield {"data": json.dumps(chat_streaming_chunk(response, "", finish_reason="stop"))}
            yield "[DONE]"

        return EventSourceResponse(generator())

    app.add_api_route("/v1/chat/completions", chat_completions, methods=["POST"], response_model=ChatCompletionResponse)


def _convert_messages(messages: list[Message]) -> list[ChatCompletionMessageParam]:
    ret = []
    for message in messages:
        if message.role == "system":
            ret.append(ChatCompletionSystemMessageParam(role="system", content=message.content))
        elif message.role == "user":
            ret.append(ChatCompletionUserMessageParam(role="user", content=message.content))
        elif message.role == "assistant":
            ret.append(ChatCompletionAssistantMessageParam(role="assistant", content=message.content))
        else:
            raise ValueError(f"Unknown role: {message.role}")
    return ret
