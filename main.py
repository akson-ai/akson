from textwrap import dedent

import gradio as gr
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

import chat_interface
import registry
from loader import load_agents

load_dotenv()

agent_classes = load_agents()

app = FastAPI()

for AgentClass in agent_classes.values():
    registry.register(AgentClass)
    gr.mount_gradio_app(app, chat_interface.create(AgentClass), f"/agents/{AgentClass.name}")


@app.get("/")
async def index():
    return RedirectResponse("/agents")


@app.get("/agents", response_class=HTMLResponse)
async def get_agents():
    return dedent(
        f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Crowd</title>
                <link rel="stylesheet" href="/style.css">
            </head>
            <body>
                <h1>Agents</h1>
                <ul>
                {"".join([f"<li><a href='/agents/{agent.name}'>{agent.name}</a></li>"
                         for agent in agent_classes.values()])}
                </ul>
            </body>
        </html>
        """
    ).strip()


@app.get("/style.css")
async def styles():
    return FileResponse("style.css")
