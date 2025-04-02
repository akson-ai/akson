from typing import Generator

from gradio.blocks import Blocks
from gradio.components import Chatbot, Markdown, Textbox
from gradio.components.chatbot import Message, MessageDict

from framework import Agent


def get_previous_messages(agent: Agent) -> list[Message | MessageDict]:
    messages = []
    for message in agent.history():
        role, content = str(message["role"]), str(message["content"])
        if role in ["user", "assistant"]:
            messages.append(Message(role=role, content=content))
    return messages


def create(agent: Agent) -> Blocks:
    def respond(prompt: str, history: list[dict[str, str]]) -> Generator[list[dict[str, str]], None, None]:
        user_message = {"role": "user", "content": prompt}
        history.append(user_message)
        yield history

        for reply in agent.message(prompt):
            assistant_message = {"role": "assistant", "content": reply}
            history.append(assistant_message)
            yield history

    with Blocks(title=agent.name) as demo:
        Markdown(f"<h1 style='text-align: center; margin-bottom: 1rem'>{agent.name}</h1>")
        Markdown(f"<p style='text-align: center'>{agent.description}</p>")
        chatbot = Chatbot(get_previous_messages(agent), type="messages")
        prompt = Textbox(max_lines=1, label="Input", placeholder=f"Reply to {agent.name}...", autofocus=True)
        prompt.submit(respond, [prompt, chatbot], [chatbot])
        prompt.submit(lambda: "", None, [prompt])
        return demo
