"""
This module contains the dynamic object loader mechanism for loading assistants.
"""

from importlib import import_module
from pathlib import Path
from typing import Iterator

from logger import logger


def load_objects[T](ObjectType: type[T], dirname: str, level: int = 0) -> Iterator[T]:
    logger.info("Loading %s objects from directory: %s", ObjectType.__name__, dirname)
    for file_path in Path(dirname).iterdir():
        if file_path.name == "__pycache__":
            continue
        if file_path.is_dir() and level > 0:
            yield from load_objects(ObjectType, str(file_path), level - 1)
            continue
        if not file_path.suffix == ".py":
            continue
        module_path = ".".join(file_path.with_suffix("").parts)
        logger.info("Importing module: %s", module_path)
        module = import_module(module_path)
        for key, value in vars(module).items():
            if isinstance(value, ObjectType):
                logger.debug("Loaded object: %s", key)
                yield value
