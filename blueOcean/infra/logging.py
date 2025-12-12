import logging
import sys
from datetime import datetime
from queue import Queue

log_queue = Queue()


class StreamlitHandler(logging.Handler):
    def __init__(self, queue: Queue = log_queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        self.queue.put(self.format(record))


logger = logging.getLogger("blueOcean")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] | %(processName)s | %(threadName)s | %(module)s | %(message)s"
)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if hasattr(sys.modules["__main__"], "__file__"):
        file_handler = logging.FileHandler(f"logs/{datetime.now()}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    streamlit_handler = StreamlitHandler()
    streamlit_handler.setLevel(logging.DEBUG)
    streamlit_handler.setFormatter(formatter)
    logger.addHandler(streamlit_handler)
