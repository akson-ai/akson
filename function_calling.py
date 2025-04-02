import json
from abc import ABC, abstractmethod
from inspect import Parameter, getdoc, signature
from typing import Callable, get_type_hints

import docstring_parser
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import pydantic_function_tool
from openai.types.chat import (
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ParsedFunctionToolCall,
)
from openai.types.shared_params import FunctionDefinition
from pydantic import Field, create_model

from logger import logger


class Toolkit(ABC):

    @abstractmethod
    async def get_tools(self) -> list[ChatCompletionToolParam]: ...

    @abstractmethod
    async def handle_tool_calls(
        self, tool_calls: list[ParsedFunctionToolCall]
    ) -> list[ChatCompletionToolMessageParam]: ...


class FunctionToolkit(Toolkit):
    """Manages the list of tools to be passed into completion reqeust."""

    def __init__(self, functions: list[Callable]) -> None:
        self.functions = {f.__name__: f for f in functions}
        self.models = {f.__name__: function_to_pydantic_model(f) for f in functions}
        self.tools = [pydantic_function_tool(model) for model in self.models.values()]

    async def get_tools(self) -> list[ChatCompletionToolParam]:
        """Returns the list of tools to be passed into completion reqeust."""
        return self.tools

    async def handle_tool_calls(self, tool_calls: list[ParsedFunctionToolCall]) -> list[ChatCompletionToolMessageParam]:
        """This is called each time a response is received from completion method."""
        logger.info("Number of tool calls: %s", len(tool_calls))
        messages = []
        for tool_call in tool_calls:
            function = tool_call.function
            logger.info("Tool call: %s(%s)", function.name, function.parsed_arguments)
            instance = function.parsed_arguments
            func = self.functions[function.name]
            model = self.models[function.name]
            assert isinstance(instance, model)
            kwargs = {name: getattr(instance, name) for name in model.model_fields}

            # Fill in default values
            for param in signature(func).parameters.values():
                if param.default is not Parameter.empty:
                    kwargs[param.name] = param.default

            result = func(**kwargs)
            logger.info("%s call result: %s", function.name, result)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

        return messages


def function_to_pydantic_model(func):
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
        if param.default is not Parameter.empty:
            type_hint |= None

        fields[param_name] = (type_hint, Field(description=param_descriptions.get(param_name, None)))

    return create_model(func.__name__, __doc__=func_description, **fields)


class MCPToolkit(Toolkit):

    def __init__(self, command: str, args: list[str] = []):
        self.server_params = StdioServerParameters(command=command, args=args)

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

    async def handle_tool_calls(self, tool_calls: list[ParsedFunctionToolCall]) -> list[ChatCompletionToolMessageParam]:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                output = []
                for tool_call in tool_calls:
                    logger.info(f"Executing tool call: {tool_call}")
                    arguments = tool_call.function.parsed_arguments
                    assert isinstance(arguments, dict)
                    result = await session.call_tool(tool_call.function.name, arguments=arguments)
                    logger.debug(f"Result: {result}")
                    output.append(
                        {
                            "role": "tool",
                            "content": str(result),
                            "tool_call_id": tool_call.id,
                        }
                    )
                return output
