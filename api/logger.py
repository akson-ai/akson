import logging
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

load_dotenv()

LEVEL = os.getenv("LOG_LEVEL", "INFO")

FORMAT = "%(message)s"

handler = RichHandler(console=Console(file=sys.stderr))
handler.setFormatter(logging.Formatter(FORMAT, datefmt="[%X]"))

logger = logging.getLogger("rich")
logger.setLevel(logging.getLevelNamesMapping()[LEVEL])
logger.addHandler(handler)
