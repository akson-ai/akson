import os

import httpx

from akson import Assistant, Chat

PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]


class Perplexity(Assistant):

    async def run(self, chat: Chat) -> None:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sonar",  # https://docs.perplexity.ai/models/model-cards
            "messages": self._get_messages(chat),
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            try:
                response.raise_for_status()
            except Exception:
                print(response.text)
                raise

        data = response.json()
        message = data["choices"][0]["message"]
        assert message["role"] == "assistant"
        reply = await chat.reply("assistant", "Perplexity")
        await reply.add_chunk(message["content"])
        await reply.end()

        citations = "\n".join(f"{i}. {citation}" for i, citation in enumerate(data["citations"], 1))
        reply = await chat.reply("assistant", "Perplexity")
        await reply.add_chunk(citations)
        await reply.end()

    # Takes care of "After the (optional) system message(s), user and assistant roles should be alternating." error.
    def _get_messages(self, chat: Chat) -> list[dict]:
        messages = []
        for message in chat.state.messages:
            try:
                last_message = messages[-1]
            except IndexError:
                messages.append({"role": message.role, "content": message.content})
            else:
                if last_message["role"] == message.role:
                    last_message["content"] += "\n\n---\n\n" + message.content
                else:
                    messages.append({"role": message.role, "content": message.content})
        return messages


perplexity = Perplexity()
