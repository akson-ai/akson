from collections import OrderedDict

from akson import Assistant
from loader import load_objects


class UnknownAssistant(Exception):
    def __init__(self, name: str):
        super().__init__(f"Unknown assistant: {name}")


class Registry:

    def __init__(self):
        self._assistants = self.load_assistants()

    def load_assistants(self):
        assistants = {}
        for assistant in load_objects(Assistant, "assistants"):
            key = assistant.name.lower()
            if key in assistants:
                raise Exception(f"Duplicate assistant found for {assistant.name}")
            else:
                assistants[key] = assistant
        return OrderedDict(sorted(assistants.items()))

    def get_assistant(self, name: str) -> Assistant:
        try:
            return self._assistants[name.lower()]
        except KeyError:
            raise UnknownAssistant(name)

    @property
    def assistants(self) -> list[Assistant]:
        return list(self._assistants.values())
