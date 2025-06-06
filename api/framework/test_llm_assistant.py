import asyncio

from .function_calling import FunctionToolkit
from .llm_assistant import LLMAssistant


def test_class_llm_assistant():
    system_prompt = """
        You are a mathematician.
        You are good at math.
        You can answer questions about math.
    """

    def add_two_numbers(a: int, b: int) -> int:
        """
        Add two numbers

        Args:
          a (int): The first number
          b (int): The second number

        Returns:
          int: The sum of the two numbers
        """
        return a + b

    mathematician = LLMAssistant(
        name="Mathematician",
        system_prompt=system_prompt,
        toolkit=FunctionToolkit([add_two_numbers]),
    )
    message = asyncio.run(mathematician.respond("What is three plus one?"))
    print("Response:", message)
