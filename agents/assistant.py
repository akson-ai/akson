import io
import os
from datetime import datetime
from typing import Generator, Literal

import gradio as gr
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent
from PIL import Image
from pydantic import BaseModel, Field

from agent import Agent
from loader import load_tools

from .prompts import (
    aggregate_prompt,
    black_hat_prompt,
    blue_hat_prompt,
    green_hat_prompt,
    red_hat_prompt,
    white_hat_prompt,
    yellow_hat_prompt,
)

load_dotenv()

tools = load_tools()

model = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=os.environ["OPENAI_API_VERSION"],
    temperature=0,
)


class Subtask(BaseModel):
    subtask: str
    tool: str


class Plan(BaseModel):
    subtasks: list[Subtask]


class AgentState(MessagesState):
    intent: str
    task: str
    plan: Plan
    step: int
    execution_result: str


def detect_intent(state: AgentState):

    class UserIntent(BaseModel):
        intent: Literal[
            "greeting",  # To recognize when a user is initiating conversation.
            "farewell",  # To handle when a user is concluding conversation.
            "question",  # When a user asks for information (e.g., "What is the weather today?").
            "task",  # Users might initiate or assign tasks (e.g., "Schedule a meeting").
            "decision",  # For decisions (e.g., "What do you think about that?").
            "suggestion",  # To handle when users propose ideas or recommendations (e.g., "Can we try this solution?").
            "answer",  # For user inputs responding to prior questions (e.g., "The answer is 42").
            "solution",  # When users provide a fix or resolution (e.g., "Use method X to solve that").
            "feedback",  # Handling user inputs that provide opinions or feedback (e.g., "This solution works well").
            "clarification",  # Recognizing when users seek more information (e.g., "What do you mean by that?").
            "confirmation",  # When users indicate agreement or approval (e.g., "Yes, that works").
            "negation",  # To handle denial or disagreement (e.g., "No, that's not correct").
            "chit_chat",  # For general small talk or social interactions (e.g., "How are you doing?").
            "other",  # For any other intents that are not explicitly defined.
        ] = Field(description="User's intent in the last message")

    system_prompt = """
        You are intent recognizer.
        You will be given a chat history and user input.
        Recognize the intent of the user input.
    """
    user_message = """
        # Message History

        {% for message in history -%}
        {{ message.type }}: {{ message.content }}
        {% endfor %}

        # User Input:
        {{ user_input.content }}
    """
    prompt = ChatPromptTemplate(
        [
            ("system", system_prompt),
            ("human", user_message),
        ],
        template_format="jinja2",
    )
    llm = model.with_structured_output(UserIntent)
    chain = prompt | llm
    *history, last_message = state["messages"]
    response = chain.invoke({"history": history, "user_input": last_message})
    assert isinstance(response, UserIntent)
    print(f"Intent: {response.intent}")
    return {
        "intent": response.intent,
        "messages": [AIMessage(content=f"I detected your intent as {response.intent}")],
    }


def extract_task(state: AgentState):
    class ExtractTask(BaseModel):
        task: str

    system_prompt = """
        You are task extractor.
        You will be given a chat history and user input.
        Extract the task from the user input.
    """
    user_message = """
        # Message History

        {% for message in history -%}
        {{ message.type }}: {{ message.content }}
        {% endfor %}

        # User Input:
        {{ user_input.content }}
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_message),
        ],
        template_format="jinja2",
    )
    llm = model.with_structured_output(ExtractTask)
    chain = prompt | llm
    *history, last_message = state["messages"]
    response = chain.invoke({"history": history, "user_input": last_message})
    assert isinstance(response, ExtractTask)
    print(f"Task: {response.task}")
    return {"task": response.task}


def planner(state: AgentState):
    class DivideSubtasks(BaseModel):
        plan: Plan

    system_prompt = """
        You are a helpful assistant that divides the given task into subtasks.
        Match each subtask to the tool that will help complete it.

        You have access to the following tools:
        {tools}
    """
    user_message = """
        Your task is: {task}
        You have access to the following tools: {tools}
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_message),
        ]
    )
    llm = model.with_structured_output(DivideSubtasks)
    chain = prompt | llm
    response = chain.invoke(
        {
            "task": state["task"],
            "tools": ", ".join(tools.keys()),
        }
    )
    assert isinstance(response, DivideSubtasks)
    print(f"Plan: {response.plan}")
    return {"plan": response.plan}


def executor(state: AgentState):
    plan = state["plan"]
    i = state.get("step", 0)
    execution_result = state.get("execution_result", "")
    step = plan.subtasks[i]
    print(f"Executing step: {i}, tool: {step.tool}, subtask: {step.subtask}")

    system_prompt = f"""
        You are a helpful assistant for executing tasks with the given tools.

        Current date and time: {datetime.now().isoformat()}
    """
    user_message = """
        # Output of previous step:
        {output}

        # Your Task
        {task}
    """.format(
        output=execution_result, task=step.subtask
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    react = create_react_agent(model, tools=[tools[step.tool]])
    response = react.invoke({"messages": messages})
    reply = response["messages"] = response["messages"][-1].content
    return {"execution_result": reply, "step": i + 1}


def decision_maker(state: AgentState):
    perspectives = ""
    for system_prompt, name in [
        (blue_hat_prompt, "blue_hat"),
        (green_hat_prompt, "green_hat"),
        (red_hat_prompt, "red_hat"),
        (yellow_hat_prompt, "yellow_hat"),
        (white_hat_prompt, "white_hat"),
        (black_hat_prompt, "black_hat"),
    ]:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["messages"][-1].content),
        ]
        response = model.invoke(messages)
        perspectives += f"<{name}>\n{response.content}\n</{name}>\n\n"

    messages = [
        SystemMessage(content=aggregate_prompt),
        HumanMessage(content=perspectives),
    ]
    response = model.invoke(messages)
    return {"messages": [response]}


def respond(state: AgentState):
    execution_result = state.get("execution_result")
    if execution_result:
        return {"messages": [AIMessage(content=execution_result)]}

    system_prompt = """
        You are a helpful AI assistant.
        Keep a conversation going with the user.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ]
    )
    chain = prompt | model
    response = chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}


def route_task(state: AgentState) -> Literal["extract_task", "decision_maker", "respond"]:
    if state["intent"] == "task":
        return "extract_task"
    if state["intent"] == "decision":
        return "decision_maker"
    else:
        return "respond"


def execution_finished(state: AgentState) -> Literal["executor", "respond"]:
    if state["step"] == len(state["plan"].subtasks):
        return "respond"
    else:
        return "executor"


def create_graph():
    graph = StateGraph(AgentState)

    graph.add_node(detect_intent)
    graph.add_node(extract_task)
    graph.add_node(decision_maker)
    graph.add_node(planner)
    graph.add_node(executor)
    graph.add_node(respond)

    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges("detect_intent", route_task)
    graph.add_edge("extract_task", "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges("executor", execution_finished)

    graph.add_edge("decision_maker", END)

    graph.add_edge("respond", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


class Assistant(Agent):

    name = "Assistant"
    description = "An agent that helps users with their tasks."

    def __init__(self):
        self.graph = create_graph()

    def message(self, input: str, *, session_id: str | None) -> Generator[str | gr.Image, None, None]:
        png_bytes = self.graph.get_graph().draw_mermaid_png()
        yield gr.Image(Image.open(io.BytesIO(png_bytes)))

        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        state = {"messages": [HumanMessage(content=input)]}
        for state in self.graph.stream(state, stream_mode="updates", config=config):
            for node, values in state.items():
                print(f"node: {node}, state_update: {values}")
                if "messages" in values:
                    yield values["messages"][0].content


assistant = Assistant()
