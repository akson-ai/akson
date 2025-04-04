import os

import httpx
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ["BLAND_API_KEY"]

mcp = FastMCP("bland")


@mcp.tool()
async def make_call(number: str, task: str) -> str:
    """Make a telephone call

    Args:
        number (str): The number to call (e.g. +1234567890)
        task (str): The task to perform
    """

    headers = {
        "Authorization": API_KEY,
    }

    data = {
        "phone_number": number,
        "task": task,
        "voice": "June",
        "wait_for_greeting": False,
        "record": True,
        "answered_by_enabled": True,
        "noise_cancellation": False,
        "interruption_threshold": 100,
        "block_interruptions": False,
        "max_duration": 12,
        "model": "base",
        "language": "en",
        "background_track": "none",
        "endpoint": "https://api.bland.ai",
        "voicemail_action": "hangup",
    }

    url = "https://api.bland.ai/v1/calls"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run()
