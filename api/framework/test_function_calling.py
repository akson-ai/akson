import pytest
from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function

from .function_calling import FunctionToolkit


async def _test_function(f, args: str):
    toolkit = FunctionToolkit([f])
    message = await toolkit.handle_tool_calls(
        [ChatCompletionMessageToolCall(function=Function(name=f.__name__, arguments=args))]
    )
    return message[0]["content"]


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

    result = await _test_function(single_arg, '{"a": "foo"}')

    result = await _test_function(two_args, '{"a": "foo", "b": "bar"}')

    result = await _test_function(return_value, "{}")
    assert result == "baz"

    result = await _test_function(int_arg, '{"a": 1}')

    result = await _test_function(default_args, '{"a": 1, "b": null}')
    result = await _test_function(default_args, '{"a": 1}')

    result = await _test_function(untyped_args, '{"a": "foo"}')


@pytest.mark.asyncio
async def test_function_calling_with_complex_types():
    def bool_arg(flag: bool):
        assert flag is True

    def list_arg(items: list):
        assert items == ["a", "b", "c"]

    def typed_list_arg(items: list[str]):
        assert items == ["a", "b", "c"]

    def dict_arg(data: dict):
        assert data == {"name": "test", "value": 123}

    def nested_arg(data: dict):
        assert data["user"]["name"] == "John"
        assert data["user"]["profile"]["age"] == 30

    await _test_function(bool_arg, '{"flag": true}')
    await _test_function(list_arg, '{"items": ["a", "b", "c"]}')
    await _test_function(typed_list_arg, '{"items": ["a", "b", "c"]}')
    await _test_function(dict_arg, '{"data": {"name": "test", "value": 123}}')
    await _test_function(nested_arg, '{"data": {"user": {"name": "John", "profile": {"age": 30}}}}')


@pytest.mark.asyncio
async def test_function_calling_with_optional_args():
    def optional_arg(a: str, b: str = "", c: int = 0):
        assert a == "required"
        assert b is ""
        assert c == 0

    def mixed_optional_args(a: str, b: str = "default", c: int = 42):
        assert a == "required"
        assert b == "default"
        assert c == 42

    def explicit_optional_args(a: str, b: str = "default", c: int = 42):
        assert a == "required"
        assert b == "custom"
        assert c == 100

    def explicit_optional_args_with_null(a: str, b: str = "default", c: int = 42):
        assert a == "required"
        assert b == "custom"
        assert c == 42

    await _test_function(optional_arg, '{"a": "required"}')
    await _test_function(mixed_optional_args, '{"a": "required"}')
    await _test_function(explicit_optional_args, '{"a": "required", "b": "custom", "c": 100}')
    await _test_function(explicit_optional_args_with_null, '{"a": "required", "b": "custom", "c": null}')


@pytest.mark.asyncio
async def test_function_with_multiple_return_types():
    def return_string():
        return "hello world"

    def return_int():
        return 42

    def return_bool():
        return True

    def return_dict():
        return {"status": "success", "code": 200}

    def return_list():
        return [1, 2, 3, 4, 5]

    result = await _test_function(return_string, "{}")
    assert result == "hello world"

    result = await _test_function(return_int, "{}")
    assert result == "42"

    result = await _test_function(return_bool, "{}")
    assert result == "true"

    result = await _test_function(return_dict, "{}")
    assert '"status": "success"' in result
    assert '"code": 200' in result

    result = await _test_function(return_list, "{}")
    assert result == "[1, 2, 3, 4, 5]"
