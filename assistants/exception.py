from akson import Assistant, Chat


class ExceptionRaiser(Assistant):

    async def run(self, chat: Chat) -> None:
        1 / 0


exception_raiser = ExceptionRaiser()
