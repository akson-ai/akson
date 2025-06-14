import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from inspect import Parameter, getdoc, signature
from typing import Callable, get_type_hints

import docstring_parser
from fastmcp import Client as FastMCPClient
from litellm import ChatCompletionMessageToolCall
from litellm import Message as LiteLLMMessage
from openai import pydantic_function_tool
from openai.types.chat import ChatCompletionToolParam
from openai.types.shared_params import FunctionDefinition
from pydantic import BaseModel, Field, create_model

from akson import Chat, ChatState, Message
from logger import logger


@dataclass
class ToolContext:
    caller: str


class Toolkit(ABC):
    """Manages the list of tools to be passed into completion reqeust."""

    @abstractmethod
    async def get_tools(self) -> list[ChatCompletionToolParam]: ...

    @abstractmethod
    async def handle_tool_calls(
        self, tool_calls: list[ChatCompletionMessageToolCall], context: ToolContext
    ) -> list[LiteLLMMessage]: ...


class MultiToolkit(Toolkit):
    """Combines multiple toolkits into one."""

    def __init__(self, toolkits: list[Toolkit]) -> None:
        self.toolkits = toolkits

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        tools = []
        for toolkit in self.toolkits:
            tools.extend(await toolkit.get_tools())
        return tools

    async def handle_tool_calls(
        self, tool_calls: list[ChatCompletionMessageToolCall], context: ToolContext
    ) -> list[LiteLLMMessage]:
        messages = []
        for toolkit in self.toolkits:
            messages.extend(await toolkit.handle_tool_calls(tool_calls, context))
        return messages


class FunctionToolkit(Toolkit):
    """Manages the list of tools to be passed into completion reqeust."""

    def __init__(self, functions: list[Callable]) -> None:
        self.functions = {f.__name__: f for f in functions}
        self.models = {f.__name__: _function_to_pydantic_model(f) for f in functions}
        self.tools = [pydantic_function_tool(model) for model in self.models.values()]

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        """Returns the list of tools to be passed into completion reqeust."""
        return self.tools

    async def handle_tool_calls(
        self, tool_calls: list[ChatCompletionMessageToolCall], context: ToolContext
    ) -> list[LiteLLMMessage]:
        """This is called each time a response is received from completion method."""
        logger.info("Number of tool calls: %s", len(tool_calls))
        messages = []
        for tool_call in tool_calls:
            function = tool_call.function
            assert isinstance(function.name, str)
            if function.name not in self.functions:
                continue
            logger.info("Tool call: %s(%s)", function.name, function.arguments)
            func = self.functions[function.name]
            model = self.models[function.name]
            instance = model.model_validate_json(tool_call.function.arguments)
            kwargs = {name: getattr(instance, name) for name in model.model_fields}

            # Fill in default values
            for param in signature(func).parameters.values():
                if kwargs[param.name] is None and param.default is not Parameter.empty:
                    kwargs[param.name] = param.default

            if asyncio.iscoroutinefunction(func):
                result = await func(**kwargs)
            else:
                result = func(**kwargs)

            logger.info("%s call result: %s", function.name, result)
            messages.append(
                LiteLLMMessage(
                    role="tool",  # type: ignore
                    tool_call_id=tool_call.id,
                    content=result if isinstance(result, str) else json.dumps(result),
                )
            )

        return messages


def _function_to_pydantic_model(func):
    sig = signature(func)
    type_hints = get_type_hints(func)
    docstring = getdoc(func)
    func_description = None
    param_descriptions = {}
    if docstring:
        parsed_docstring = docstring_parser.parse(docstring)
        func_description = parsed_docstring.short_description
        if parsed_docstring:
            for param in parsed_docstring.params:
                param_descriptions[param.arg_name] = param.description

    fields = {}
    for param_name, param in sig.parameters.items():
        type_hint = type_hints.get(param_name, str)

        # All fields are required. Optional parameters are emulated by using a union type with null.
        default_value = ...
        if param.default is not Parameter.empty:
            type_hint |= None
            default_value = param.default

        fields[param_name] = (type_hint, Field(default=default_value, description=param_descriptions.get(param_name)))

    return create_model(func.__name__, __doc__=func_description, **fields)


class MCPToolkit(Toolkit):

    def __init__(self, client: FastMCPClient):
        self.client = client
        self._initialized = False
        self._lock = asyncio.Lock()
        self._tools: list[ChatCompletionToolParam] = []

    @classmethod
    def from_config(cls, command: str, args: list[str] = [], env: dict[str, str] = {}):
        return cls(FastMCPClient({"mcpServers": {"": {"command": command, "args": args, "env": env}}}))

    @classmethod
    def from_node_package(cls, package: str, **kargs):
        cmd = node_package(package, **kargs)
        env = dict(kargs.get("env", []))
        return cls(FastMCPClient({"mcpServers": {"": {"command": cmd[0], "args": cmd[1:], "env": env}}}))

    @classmethod
    def from_docker_image(cls, image: str, **kargs):
        cmd = docker_command(image, **kargs)
        env = dict(kargs.get("env", []))
        return cls(FastMCPClient({"mcpServers": {"": {"command": cmd[0], "args": cmd[1:], "env": env}}}))

    async def _initialize(self):
        async with self._lock:
            if not self._initialized:
                await self.client._connect()
                await self._get_tools()
                self._initialized = True

    async def _get_tools(self):
        tools = await self.client.list_tools()
        logger.info(f"Got {len(tools)} tools.")
        for tool in tools:
            schema = dict(tool.inputSchema)
            schema["required"] = list(schema["properties"].keys())
            schema["additionalProperties"] = False
            param = ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=schema,
                    strict=True,
                ),
            )
            self._tools.append(param)
            logger.info(f"Added tool from MCP server: {tool.name}")

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        await self._initialize()
        return self._tools

    async def handle_tool_calls(
        self, tool_calls: list[ChatCompletionMessageToolCall], context: ToolContext
    ) -> list[LiteLLMMessage]:
        await self._initialize()
        output = []
        for tool_call in tool_calls:
            if (tool_call.function.name or "") not in (tool["function"]["name"] for tool in self._tools):
                continue
            logger.info(f"Executing tool call: {tool_call}")
            arguments = json.loads(tool_call.function.arguments)
            assert isinstance(arguments, dict)
            assert isinstance(tool_call.function.name, str)
            result = await self.client.call_tool(tool_call.function.name, arguments=arguments)
            logger.debug(f"Result: {result}")
            result_str = "\n\n".join(content.text for content in result if content.type == "text")
            output.append(
                LiteLLMMessage(
                    role="tool",  # type: ignore
                    content=result_str,
                    tool_call_id=tool_call.id,
                )
            )
        return output


class TaskStatus(StrEnum):
    INPUT_REQUIRED = "INPUT_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskAnalysis(BaseModel):
    status: TaskStatus
    result: str | None = Field(default=None, description="Result of the task (e.g. the data requested by user)")


class TaskResponse(BaseModel):
    id: str
    analysis: TaskAnalysis


class AssistantToolkit(Toolkit):

    TOOL_NAME = "delegate_task"

    def __init__(self, assistants: list[str]):
        self.assitants = assistants

        assistant_enum = StrEnum("Assistant", self.assitants)

        class DelegateTask(BaseModel):
            """
            Delegate a task to an assistant.
            """

            assistant: assistant_enum
            task: str
            id: str | None = Field(
                default=None,
                description=(
                    "ID of the task. Used to track the task."
                    "Pass null if you want to start a new conversation. The tool will generate a new ID."
                    "Pass the same ID if you want to continue the conversation."
                ),
            )

        self._model = DelegateTask
        self._tools = [pydantic_function_tool(self._model, name=self.TOOL_NAME)]

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        return self._tools

    async def handle_tool_calls(
        self, tool_calls: list[ChatCompletionMessageToolCall], context: ToolContext
    ) -> list[LiteLLMMessage]:
        ret = []
        for tool_call in tool_calls:
            if tool_call.function.name != self.TOOL_NAME:
                continue
            logger.info(f"Executing tool call: {tool_call}")
            instance = self._model.model_validate_json(tool_call.function.arguments)
            task_response = await self._complete_task(instance, context.caller)
            logger.debug(f"Task response: {task_response}")
            ret.append(
                LiteLLMMessage(
                    role="tool",  # type: ignore
                    content=task_response.model_dump_json(),
                    tool_call_id=tool_call.id,
                )
            )
        return ret

    async def _complete_task(self, tool_call, assistant_name: str) -> TaskResponse:
        from deps import registry
        from framework import LLMAssistant

        if tool_call.id:
            chat = Chat(state=ChatState.load_from_disk(tool_call.id))
        else:
            chat = Chat()

        # Run the assistant on the task's chat session
        assistant = registry.get_assistant(tool_call.assistant)
        chat.state.assistant = assistant.name
        chat.state.messages.append(Message(role="user", name=assistant_name, content=tool_call.task))
        await assistant.run(chat)

        task_analyzer = LLMAssistant(
            name="TaskAnalyzer",
            model="gpt-4.1",
            system_prompt="""
            Analyze the conversation and extract the task details and output.
            You must extract all details asked from the conversation because the user cannot see this conversation.
            For example if user is asking for email, you must extract the list of emails and output them.
            """,
            output_type=TaskAnalysis,
        )

        temp = Chat()
        temp.state.messages = chat.state.messages.copy()
        await task_analyzer.run(temp)

        analysis = TaskAnalysis.model_validate_json(temp.state.messages[-1].content)
        chat.state.save_to_disk()

        return TaskResponse(id=chat.state.id, analysis=analysis)


def clean_string(text):
    """Remove all characters except a-z, A-Z, 0-9, dash, and underscore"""
    return "".join(char for char in text if char.isalnum() or char in "_-")


def docker_command(
    image: str,
    *,
    name: str | None = None,
    args: list[str] = [],
    env: list[tuple[str, str]] = [],
    entrypoint: str | None = None,
    mounts: list[tuple[str, str]] = [],
    volumes: list[tuple[str, str]] = [],
):
    cmd = ["docker", "run", "-i", "--rm"]
    if name:
        name = clean_string(name)
        cmd.extend(["--name", f"akson-{name}"])
    if entrypoint:
        cmd.extend(["--entrypoint", entrypoint])
    for mount in mounts:
        cmd.extend(["--mount", f"type=bind,source={mount[0]},target={mount[1]}"])
    for volume in volumes:
        cmd.extend(["-v", f"{volume[0]}:{volume[1]}"])
    for env_var in env:
        cmd.extend(["-e", f"{env_var[0]}={env_var[1]}"])
    cmd.append(image)
    cmd.extend(args)
    return cmd


def node_package(package: str, **kwargs):
    NPM_CACHE_DIR = os.environ["NPM_CACHE_DIR"]
    kwargs["args"] = ["exec", package] + kwargs.get("args", [])
    kwargs["mounts"] = kwargs.get("mounts", []) + [(NPM_CACHE_DIR, "/root/.npm")]
    return docker_command("node:24", name=package, entrypoint="/usr/local/bin/npm", **kwargs)
