import importlib
import os
from typing import Callable

from langchain_core.tools.structured import StructuredTool

from agent import Agent
from logger import logger


def load_agents() -> dict[str, type[Agent]]:
    return load_objects("agents", _filter_agents)  # type: ignore


def load_tools() -> dict[str, StructuredTool]:
    return load_objects("tools", _filter_tools)  # type: ignore


def _filter_agents(value):
    if not isinstance(value, type):
        return False
    if value is Agent:
        return False
    if not issubclass(value, Agent):
        return False
    return True


def _filter_tools(value):
    if not isinstance(value, StructuredTool):
        return False
    return True


def load_objects(dirname: str, filter_func: Callable) -> dict[str, object]:
    objects = {}
    objects_dir = os.path.join(os.path.dirname(__file__), dirname)
    logger.info("Loading objects from directory: %s", objects_dir)
    for object_file in os.listdir(objects_dir):
        object_file = os.path.basename(object_file)
        module_name, extension = os.path.splitext(object_file)
        if extension != ".py":
            continue
        logger.info("Loading file: %s", object_file)
        module_name = f"{dirname}.{module_name}"
        module = importlib.import_module(module_name)
        for key, value in vars(module).items():
            if not filter_func(value):
                continue
            objects[key] = value
            logger.info("Object loaded: %s", key)
    return objects
