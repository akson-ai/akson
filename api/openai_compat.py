import json
import random
import time
from typing import Iterable, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse

from akson import Chat
from akson import Message as AksonMessage
from deps import registry
from runner import Runner


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


def setup_routes(app: FastAPI):
    async def chat_completions(request: ChatCompletionRequest):
        assistant = registry.get_assistant(request.model)

        chat = Chat()
        chat.state.messages = list(_convert_messages(request.messages))

        runner = Runner(assistant, chat)
        new_messages = await runner.run()
        content = new_messages[-1].content

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

    # TODO add /v1/models endpoint
    app.add_api_route("/v1/chat/completions", chat_completions, methods=["POST"], response_model=ChatCompletionResponse)


def _convert_messages(messages: list[Message]) -> Iterable[AksonMessage]:
    for message in messages:
        match message.role:
            case "system" | "user":
                yield AksonMessage(role="user", content=message.content)
            case "assistant":
                yield AksonMessage(role="assistant", content=message.content)
            case _:
                raise ValueError(f"Unknown role: {message.role}")
