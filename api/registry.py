from collections import OrderedDict

from akson import Assistant
from loader import load_objects


class UnknownAssistant(Exception):
    def __init__(self, name: str):
        super().__init__(f"Unknown assistant: {name}")


class Registry:

    def __init__(self):
        # Keys are lowercase assistant names
        self._assistants: dict[str, Assistant] = self._load_assistants()

    def _load_assistants(self):
        assistants = {}
        for assistant in load_objects(Assistant, "assistants", level=1):
            key = assistant.name.lower()
            if key in assistants:
                raise Exception(f"Duplicate assistant found for {assistant.name}")
            else:
                assistants[key] = assistant
        return OrderedDict(sorted(assistants.items()))

    def get_assistant(self, name: str) -> Assistant:
        name = name.lower()
        try:
            return self._assistants[name]
        except KeyError:
            matches = [assistant for assistant in self.assistants if assistant.name.lower().startswith(name)]
            if len(matches) == 1:
                return matches[0]
            raise UnknownAssistant(name)

    @property
    def assistants(self) -> list[Assistant]:
        return list(self._assistants.values())
