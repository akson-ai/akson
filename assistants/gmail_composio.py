import rich

# from composio_openai import ComposioToolSet
from openai.types.chat import (
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ParsedFunctionToolCall,
)

from framework import SimpleAssistant, Toolkit
from logger import logger


class ComposioToolkit(Toolkit):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.toolkit = ComposioToolSet()

    def get_tools(self) -> list[ChatCompletionToolParam]:
        logger.info("Getting tools...")
        # print(f"args: {self.args}, kwargs: {self.kwargs}")
        tools = self.toolkit.get_tools(*self.args, **self.kwargs)
        logger.info(f"Got {len(tools)} tools.")
        for tool in tools:
            tool["function"]["strict"] = True
            parameters = tool["function"].setdefault("parameters", {})
            parameters["additionalProperties"] = False
            properties = parameters.get("properties")
            assert isinstance(properties, dict)

            for property in properties.values():
                # 'default' is not permitted
                if "default" in property:
                    del property["default"]

                # 'minimum' is not permitted
                if "minimum" in property:
                    property["description"] += f" Minimum: {property['minimum']}"
                    del property["minimum"]

                # 'maximum' is not permitted
                if "maximum" in property:
                    property["description"] += f" Maximum: {property['maximum']}"
                    del property["maximum"]

                # 'examples' is not permitted
                if "examples" in property:
                    examples = property["examples"]
                    examples = ", ".join(str(example) for example in examples if example)
                    property["description"] += f" Examples: {examples}"
                    del property["examples"]

            # 'required' is required
            parameters["required"] = list(properties.keys())

        rich.print(tools)
        return tools

    def handle_tool_calls(self, tool_calls: list[ParsedFunctionToolCall]) -> list[ChatCompletionToolMessageParam]:
        print(f"Executing {len(tool_calls)} tool calls...")
        output = []
        for tool_call in tool_calls:
            print(f"Executing tool call: {tool_call}")
            result = self.toolkit.execute_tool_call(tool_call=tool_call)
            print(f"Result: {result}")
            assert result["successful"]
            output.append(
                {
                    "role": "tool",
                    "content": str(result["data"]),
                    "tool_call_id": tool_call.id,
                }
            )
        return output


# gmail_composio = SimpleAssistant(
#     name="Gmail (Composio)",
#     system_prompt="You are Gmail assistant.",
#     toolkit=ComposioToolkit(
#         actions=[
#             "GMAIL_GET_PROFILE",
#             "GMAIL_LIST_THREADS",
#             "GMAIL_LIST_LABELS",
#             "GMAIL_GET_PEOPLE",
#             "GMAIL_SEARCH_PEOPLE",
#             "GMAIL_GET_CONTACTS",
#         ]
#     ),
# )
