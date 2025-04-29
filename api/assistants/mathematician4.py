from framework import Agent, FunctionToolkit

system_prompt = """
    You are a mathematician but you can only add two numbers.
    Refuse operations other than addition.
    Use add_two_numbers function to add two numbers.
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


toolkit = FunctionToolkit([add_two_numbers])

mathematician4 = Agent(name="Mathematician 4", system_prompt=system_prompt, toolkit=toolkit)
