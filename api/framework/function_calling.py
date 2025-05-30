import asyncio
import json
from abc import ABC, abstractmethod
from inspect import Parameter, getdoc, signature
from typing import Callable, get_type_hints

import docstring_parser
from litellm import ChatCompletionMessageToolCall, Message
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import pydantic_function_tool
from openai.types.chat import ChatCompletionToolParam
from openai.types.shared_params import FunctionDefinition
from pydantic import Field, create_model

from logger import logger


class Toolkit(ABC):
    """Manages the list of tools to be passed into completion reqeust."""

    @abstractmethod
    async def get_tools(self) -> list[ChatCompletionToolParam]: ...

    @abstractmethod
    async def handle_tool_calls(self, tool_calls: list[ChatCompletionMessageToolCall]) -> list[Message]: ...


class FunctionToolkit(Toolkit):
    """Manages the list of tools to be passed into completion reqeust."""

    def __init__(self, functions: list[Callable]) -> None:
        self.functions = {f.__name__: f for f in functions}
        self.models = {f.__name__: _function_to_pydantic_model(f) for f in functions}
        self.tools = [pydantic_function_tool(model) for model in self.models.values()]

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        """Returns the list of tools to be passed into completion reqeust."""
        return self.tools

    async def handle_tool_calls(self, tool_calls: list[ChatCompletionMessageToolCall]) -> list[Message]:
        """This is called each time a response is received from completion method."""
        logger.info("Number of tool calls: %s", len(tool_calls))
        messages = []
        for tool_call in tool_calls:
            function = tool_call.function
            assert isinstance(function.name, str)
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
                Message(
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

    def __init__(self, command: str, args: list[str] = [], env: dict[str, str] | None = None):
        self.server_params = StdioServerParameters(command=command, args=args, env=env)

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                out = []
                tools = await session.list_tools()
                logger.info(f"Got {len(tools.tools)} tools.")
                for tool in tools.tools:
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
                    out.append(param)
                return out

    async def handle_tool_calls(self, tool_calls: list[ChatCompletionMessageToolCall]) -> list[Message]:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                output = []
                for tool_call in tool_calls:
                    logger.info(f"Executing tool call: {tool_call}")
                    arguments = json.loads(tool_call.function.arguments)
                    assert isinstance(arguments, dict)
                    assert isinstance(tool_call.function.name, str)
                    result = await session.call_tool(tool_call.function.name, arguments=arguments)
                    logger.debug(f"Result: {result}")
                    output.append(
                        Message(
                            role="tool",  # type: ignore
                            content=str(result),
                            tool_call_id=tool_call.id,
                        )
                    )
                return output
