import json
from typing import Optional

import httpx


class AksonClient:

    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=None)

    async def get_assistants(self) -> list[str]:
        response = await self.client.get(f"/assistants")
        response.raise_for_status()
        # TODO return list of objects
        return [assistant["name"] for assistant in response.json()]

    async def set_assistant(self, chat_id: str, assistant: str) -> None:
        response = await self.client.put(
            f"/{chat_id}/assistant",
            headers={"Content-Type": "text/plain"},
            content=assistant.encode(),
        )
        response.raise_for_status()

    async def get_chat_state(self, chat_id: str) -> dict:
        response = await self.client.get(f"/{chat_id}/state")
        response.raise_for_status()
        return response.json()

    async def send_message(
        self, chat_id: str, content: str, *, assistant: Optional[str] = None, message_id: Optional[str] = None
    ) -> list[dict]:
        data = {"content": content}
        if assistant:
            data["assistant"] = assistant
        if message_id:
            data["id"] = message_id
        response = await self.client.post(f"/{chat_id}/message", json=data)
        response.raise_for_status()
        return response.json()

    async def stream_events(self, chat_id: str):
        async with self.client.stream("GET", f"/{chat_id}/events", timeout=None) as response:
            async for line in response.aiter_lines():
                prefix = "data: "
                if line.startswith(prefix):
                    data = json.loads(line[len(prefix) :])
                    yield data
