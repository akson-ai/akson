from litellm.types.utils import Delta, Message

from .streaming import Event, MessageBuilder, StrValue, Values


def test_str_value_basic():
    value = StrValue()
    assert not value
    value.write("test")
    assert value
    assert value.getvalue() == "test"


def test_str_value_streamable():
    value = StrValue(streamable=True)
    value.write("t")
    value.write("e")
    value.write("s")
    value.write("t")
    assert value.getvalue() == "test"


def test_str_value_with_event():
    value = StrValue(event_name="test_event")
    event = value.write("test")
    assert isinstance(event, Event)
    assert event.name == "test_event"
    assert event.chunk == "test"


def test_str_value_none_chunk():
    value = StrValue()
    event = value.write(None)
    assert event is None
    assert not value


def test_values_basic():
    values = Values(
        test1=StrValue(),
        test2=StrValue(),
    )
    values.write("test1", "value1")
    values.write("test2", "value2")
    assert values["test1"] == "value1"
    assert values["test2"] == "value2"


def test_values_events():
    values = Values(
        test1=StrValue(event_name="event1"),
        test2=StrValue(event_name="event2"),
    )
    values.write("test1", "value1")
    values.write("test2", "value2")
    events = values.getevents()
    assert len(events) == 2
    assert events[0].name == "event1"
    assert events[0].chunk == "value1"
    assert events[1].name == "event2"
    assert events[1].chunk == "value2"


def test_message_builder_basic():
    builder = MessageBuilder()
    delta = Delta(role="user", content="Hello")
    builder.write(delta)
    message = builder.getvalue()

    assert isinstance(message, Message)
    assert message.role == "user"
    assert message.content == "Hello"
    assert message.tool_calls is None


def test_message_builder_with_tool_call():
    builder = MessageBuilder()
    delta = Delta(
        role="assistant",
        content="",
        tool_calls=[
            {
                "index": 0,
                "id": "test_id",
                "type": "function",
                "function": {"name": "test_function", "arguments": '{"arg1": "value1"}'},
            }
        ],
    )
    events = builder.write(delta)
    print(f"events: {events}")
    message = builder.getvalue()

    assert isinstance(message, Message)
    assert message.role == "assistant"
    assert message.content == ""
    assert message.tool_calls is not None
    assert len(message.tool_calls) == 1
    tool_call = message.tool_calls[0]
    assert tool_call.id == "test_id"
    assert tool_call.type == "function"
    assert tool_call.function.name == "test_function"
    assert tool_call.function.arguments == '{"arg1": "value1"}'


def test_message_builder_streaming():
    builder = MessageBuilder()

    # First delta with role
    delta1 = Delta(role="assistant", content="Hello")
    events1 = builder.write(delta1)
    assert len(events1) == 2  # role and content events

    # Second delta with more content
    delta2 = Delta(content=" world")
    events2 = builder.write(delta2)
    assert len(events2) == 1  # only content event

    message = builder.getvalue()
    assert message.role == "assistant"
    assert message.content == "Hello world"


def test_message_builder_streaming_tool_call():
    builder = MessageBuilder()

    # First delta with role and tool call start
    delta1 = Delta(
        role="assistant",
        content="",
        tool_calls=[{"index": 0, "id": "test_id", "type": "function", "function": {"name": "test", "arguments": ""}}],
    )
    builder.write(delta1)

    # Second delta with function arguments
    delta2 = Delta(tool_calls=[{"index": 0, "function": {"arguments": '{"arg1": "value1"}'}}])
    builder.write(delta2)

    message = builder.getvalue()
    assert message.tool_calls is not None
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0].function.arguments == '{"arg1": "value1"}'