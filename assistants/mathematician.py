from framework import DeclarativeAssistant


class Mathematician(DeclarativeAssistant):
    """
    You are a mathematician but you can only add two numbers.
    Refuse operations other than addition and substraction.
    Use add_two_numbers function to add two numbers.
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

    def substract_two_numbers(self, a: int, b: int) -> int:
        """
        Subtract two numbers

        Args:
          a (int): The first number
          b (int): The second number

        Returns:
          int: The difference of the two numbers
        """
        return a - b


mathematician = Mathematician()
