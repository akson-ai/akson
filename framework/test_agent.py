import asyncio

from .agent import ClassAgent


def test_class_agent():
    class Mathematician(ClassAgent):
        """
        You are a mathematician. You are good at math. You can answer questions about math.
        """

        def add_two_numbers(self, a: int, b: int) -> int:
            """
            Add two numbers

            Args:
              a (int): The first number
              b (int): The second number

            Returns:
              int: The sum of the two numbers
            """
            return a + b

    mathematician = Mathematician()
    message = asyncio.run(mathematician.respond("What is three plus one?"))
    print("Response:", message)
