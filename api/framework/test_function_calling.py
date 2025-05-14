import pytest
from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function

from .function_calling import FunctionToolkit


@pytest.mark.asyncio
async def test_function_calling():
    def single_arg(a: str):
        assert a == "foo"

    def two_args(a: str, b: str):
        assert a == "foo"
        assert b == "bar"

    def return_value():
        return "baz"

    def int_arg(a: int):
        assert a == 1

    def default_args(a: int, b: int = 2):
        assert a == 1
        assert b == 2

    def untyped_args(a):
        assert a == "foo"

    async def test_function(f, args: str):
        toolkit = FunctionToolkit([f])
        message = await toolkit.handle_tool_calls(
            [ChatCompletionMessageToolCall(function=Function(name=f.__name__, arguments=args))]
        )
        return message[0]["content"]

    result = await test_function(single_arg, '{"a": "foo"}')

    result = await test_function(two_args, '{"a": "foo", "b": "bar"}')

    result = await test_function(return_value, "{}")
    assert result == "baz"

    result = await test_function(int_arg, '{"a": 1}')

    result = await test_function(default_args, '{"a": 1, "b": null}')
    result = await test_function(default_args, '{"a": 1}')

    result = await test_function(untyped_args, '{"a": "foo"}')
