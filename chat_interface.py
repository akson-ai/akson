from typing import Generator

import gradio as gr

from agent import Agent


def create(AgentImpl: type[Agent]) -> gr.Blocks:
    agent = AgentImpl()

    def respond(prompt: str, history: list[dict[str, str]]) -> Generator[list[dict[str, str]], None, None]:
        user_message = {"role": "user", "content": prompt}
        history.append(user_message)
        yield history

        for reply in agent.message(prompt):
            assistant_message = {"role": "assistant", "content": reply}
            history.append(assistant_message)
            yield history

    with gr.Blocks(title=agent.name) as demo:
        gr.Markdown(f"<h1 style='text-align: center; margin-bottom: 1rem'>{agent.name}</h1>")
        gr.Markdown(f"<p style='text-align: center'>{agent.description}</p>")
        chatbot = gr.Chatbot(type="messages")
        prompt = gr.Textbox(max_lines=1, label="Input", placeholder=f"Reply to {agent.name}...", autofocus=True)
        prompt.submit(respond, [prompt, chatbot], [chatbot])
        prompt.submit(lambda: "", None, [prompt])
        return demo
