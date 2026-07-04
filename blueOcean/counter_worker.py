import os
from multiprocessing.synchronize import Event
from typing import Any

from blueOcean.logging import get_logger


logger = get_logger("counter")


def run_counter(
    stop_event: Event,
    counter_value: Any,
    worker_id: str,
    interval: float = 1.0,
) -> None:
    """Count upward in a dedicated process until requested to stop."""
    count = 0
    logger.info("Counter %s started (pid=%s)", worker_id, os.getpid())

    while not stop_event.wait(interval):
        with counter_value.get_lock():
            counter_value.value += 1
            count = counter_value.value
        logger.info("Counter %s: %s (pid=%s)", worker_id, count, os.getpid())

    logger.info("Counter %s stopped at %s (pid=%s)", worker_id, count, os.getpid())
