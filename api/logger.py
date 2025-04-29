import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

FORMAT = "%(message)s"

handler = RichHandler(console=Console(file=sys.stderr))
handler.setFormatter(logging.Formatter(FORMAT, datefmt="[%X]"))

logger = logging.getLogger("rich")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
