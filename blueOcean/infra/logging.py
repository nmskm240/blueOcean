import logging
import sys
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("blueOcean")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] | %(processName)s | %(threadName)s | %(module)s | %(message)s"
)

def _is_notebook() -> bool:
    return "ipykernel" in sys.modules

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if not _is_notebook():
        file_handler = TimedRotatingFileHandler(
            "logs/blueOcean",
            when="midnight",
            backupCount=7,
            interval=1,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
