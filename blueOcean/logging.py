import logging
from queue import Queue


log_queue = Queue()


class StreamlitHandler(logging.Handler):
    def __init__(self, queue: Queue = log_queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        self.queue.put(self.format(record))


logger = logging.getLogger("blueOcean")
logger.setLevel(logging.INFO)

if not logger.handlers:
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    streamlit = StreamlitHandler()
    streamlit.setLevel(logging.DEBUG)
    streamlit.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logger.addHandler(console)
    logger.addHandler(streamlit)
