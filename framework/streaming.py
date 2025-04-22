from io import StringIO

from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Delta,
    Function,
    Message,
)
from pydantic import BaseModel


class Event(BaseModel):
    name: str
    chunk: str


class MessageBuilder:
    """A class for building a Message object from a stream of deltas. Usage is similar to io.StringIO."""

    def __init__(self):
        self.values = Values(
            message_role=StrValue("role"),
            message_content=StrValue("content", streamable=True),
            tool_call_id=StrValue(),
            tool_call_type=StrValue(),
            function_name=StrValue("function_name", streamable=True),
            function_arguments=StrValue("function_arguments", streamable=True),
        )

    def write(self, delta: Delta) -> list[Event]:
        """Apply a delta to the current state of the builder."""
        self.values.write("message_role", delta.role)
        self.values.write("message_content", delta.content)
        if delta.tool_calls:
            assert len(delta.tool_calls) == 1
            tool_call = delta.tool_calls[0]
            assert tool_call.index == 0
            self.values.write("tool_call_id", tool_call.id)
            self.values.write("tool_call_type", tool_call.type)
            self.values.write("function_name", tool_call.function.name)
            self.values.write("function_arguments", tool_call.function.arguments)

        return self.values.getevents()

    def getvalue(self) -> Message:
        """Construct a Message object from the current state of the builder."""
        message = Message(
            role=self.values["message_role"],  # type: ignore
            content=self.values["message_content"],
        )
        if self.values["tool_call_id"]:
            message.tool_calls = [
                ChatCompletionMessageToolCall(
                    id=self.values["tool_call_id"],
                    type=self.values["tool_call_type"],
                    function=Function(
                        name=self.values["function_name"],
                        arguments=self.values["function_arguments"],
                    ),
                )
            ]
        return message


class StrValue:
    """Helper class for building a string value from a stream of chunks."""

    def __init__(self, event_name: str | None = None, streamable: bool = False):
        self.event_name = event_name
        if streamable:
            self.str = StringIO()
        else:
            self.str = None

    def __bool__(self):
        if isinstance(self.str, StringIO):
            return bool(self.str.getvalue())
        return bool(self.str)

    def write(self, chunk: str | None) -> Event | None:
        """
        Write a chunk to the string value.
        Returns an event if event_name is set.
        """
        if chunk is None:
            return
        elif isinstance(self.str, StringIO):
            self.str.write(chunk)
            if self.event_name:
                return Event(name=self.event_name, chunk=chunk)
        elif self.str is not None and self.str != chunk:
            raise ValueError("Value is not streamable")
        else:
            self.str = chunk
            if self.event_name:
                return Event(name=self.event_name, chunk=chunk)

    def getvalue(self) -> str | None:
        if isinstance(self.str, StringIO):
            return self.str.getvalue()
        else:
            return self.str


class Values:

    def __init__(self, **kwargs: StrValue):
        self._values = kwargs
        self._events = []

    def __getitem__(self, name: str) -> str | None:
        return self._values[name].getvalue()

    def write(self, name: str, chunk: str | None):
        event = self._values[name].write(chunk)
        if event:
            self._events.append(event)

    def getevents(self) -> list[Event]:
        """Get the events and clear the list of events."""
        ret, self._events = self._events, []
        return ret
