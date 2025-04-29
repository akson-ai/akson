from openai import OpenAI

client = OpenAI(
    api_key="sk-mock-api-key",  # This can be any string for our mock API
    base_url="http://localhost:8000/v1",  # Assumes the mock API is running on localhost:8000
)


def chat_with_mock_api(agent: str, message: str):
    response = client.chat.completions.create(
        model=agent,
        messages=[{"role": "user", "content": message}],
        temperature=0.7,
        max_tokens=50,
    )

    print("Mock API Response:")
    print(f"ID: {response.id}")
    print(f"Created: {response.created}")
    print(f"Model: {response.model}")
    print("Choices:")
    for choice in response.choices:
        print(f"  Role: {choice.message.role}")
        print(f"  Content: {choice.message.content}")
        print(f"  Finish Reason: {choice.finish_reason}")
    if response.usage:
        print("Usage:")
        print(f"  Prompt Tokens: {response.usage.prompt_tokens}")
        print(f"  Completion Tokens: {response.usage.completion_tokens}")
        print(f"  Total Tokens: {response.usage.total_tokens}")


def chat_with_mock_api_streaming(agent: str, message: str):
    stream_response = client.chat.completions.create(
        stream=True,
        model=agent,
        messages=[{"role": "user", "content": message}],
        temperature=0.7,
        max_tokens=50,
    )

    for response in stream_response:
        print("Mock API Response:")
        print(f"ID: {response.id}")
        print(f"Created: {response.created}")
        print(f"Model: {response.model}")
        print("Choices:")
        for choice in response.choices:
            print(f"  Role: {choice.delta.role}")
            print(f"  Content: {choice.delta.content}")
            print(f"  Finish Reason: {choice.finish_reason}")
        if response.usage:
            print("Usage:")
            print(f"  Prompt Tokens: {response.usage.prompt_tokens}")
            print(f"  Completion Tokens: {response.usage.completion_tokens}")
            print(f"  Total Tokens: {response.usage.total_tokens}")


if __name__ == "__main__":
    agent = input("Enter an agent: ")
    message = input("Enter a message: ")
    chat_with_mock_api(agent, message)
    chat_with_mock_api_streaming(agent, message)
