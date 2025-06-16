# Assistants

This folder contains AI assistants that can be used with Akson.

## Creating Custom Assistants

To create a custom assistant, simply add a Python file to this directory or in a subdirectory (1 level deep).
Akson automatically loads assistants from this directory and 1 directory level below.
Each assistant should implement the assistant interface for Akson to recognize and use it.

### Minimal Example

Here's a simple "Echo" assistant that repeats back the user's message:

```python
from akson import Assistant, Chat


class Echo(Assistant):

    async def run(self, chat: Chat) -> None:
        # Get the last message
        user_message = chat.state.messages[-1]

        # Create a reply
        reply = await chat.reply("assistant", "Echo")
        await reply.add_chunk(user_message.content)
        await reply.end()


echo = Echo()
```

### Assistant Interface

All assistants must:
1. Inherit from the `Assistant` class
2. Implement the `run(self, chat: Chat)` async method
3. Create an instance of the assistant class at module level

The `chat` parameter provides access to:
- `chat.state.messages` - conversation history
- `chat.reply()` - method to create responses
- Other chat utilities and state management

### Built-in Assistants

Akson includes several general-purpose assistants:
- `chatgpt.py` - OpenAI ChatGPT integration
- `claude.py` - Anthropic Claude integration  
- `gemini.py` - Google Gemini integration

## External Assistant Repositories

You can also maintain your own repository of custom assistants and clone it directly into this directory.
This allows you to version control your assistants separately and easily share them across different Akson installations.

```bash
# Clone your assistant repository into this directory
git clone https://github.com/yourusername/my-assistants.git
```

## Examples and Documentation

For more examples and advanced usage patterns, see: https://github.com/cenkalti/assistants
