import importlib
import os
from typing import TypeVar

from akson import Assistant
from logger import logger


def load_assistants() -> dict[str, Assistant]:
    return load_objects(Assistant, "assistants")


T = TypeVar("T")


def load_objects(object_type: type[T], dirname: str) -> dict[str, T]:
    objects = {}
    objects_dir = os.path.join(os.path.dirname(__file__), dirname)
    logger.info("Loading %s objects from directory: %s", object_type.__name__, objects_dir)
    for object_file in os.listdir(objects_dir):
        object_file = os.path.basename(object_file)
        module_name, extension = os.path.splitext(object_file)
        if extension != ".py":
            continue
        logger.debug("Loading file: %s", object_file)
        module_path = f"{dirname}.{module_name}"
        module = importlib.import_module(module_path)
        for key, value in vars(module).items():
            if not isinstance(value, object_type):
                continue
            object_id = f"{module_name}.{key}"
            objects[object_id] = value
            logger.info("Object loaded: %s", key)
    return objects
