import importlib
import os
from typing import Iterator

from logger import logger


def load_objects[T](ObjectType: type[T], dirname: str, level: int = 0) -> Iterator[T]:
    objects_dir = os.path.join(os.path.dirname(__file__), dirname)
    logger.info("Loading %s objects from directory: %s", ObjectType.__name__, objects_dir)
    for object_file in os.listdir(objects_dir):
        if level > 0:
            sub_dir = os.path.join(dirname, object_file)
            yield from load_objects(ObjectType, sub_dir, level - 1)
        object_file = os.path.basename(object_file)
        module_name, extension = os.path.splitext(object_file)
        if extension != ".py":
            continue
        logger.debug("Loading file: %s", object_file)
        module_path = f"{dirname}.{module_name}"
        module = importlib.import_module(module_path)
        for key, value in vars(module).items():
            if not isinstance(value, ObjectType):
                continue
            logger.info("Loaded object: %s", key)
            yield value
