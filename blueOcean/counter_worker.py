import os
import time

from blueOcean.counter_repository import RedisCounterRepository
from blueOcean.logging import get_logger


logger = get_logger("counter")


def run_counter(redis_url: str, worker_id: str, interval: float = 1.0) -> None:
    """Count in a dedicated process, using Redis for state and control."""
    repository = RedisCounterRepository(redis_url)
    count = 0
    repository.mark_running(worker_id, os.getpid())
    logger.info("Counter %s started (pid=%s)", worker_id, os.getpid())

    while True:
        time.sleep(interval)
        if repository.should_stop(worker_id):
            break
        count = repository.increment(worker_id)
        logger.info("Counter %s: %s (pid=%s)", worker_id, count, os.getpid())

    repository.mark_stopped(worker_id)
    logger.info("Counter %s stopped at %s (pid=%s)", worker_id, count, os.getpid())
