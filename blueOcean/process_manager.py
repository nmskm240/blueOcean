from multiprocessing import Process
from threading import Lock
from uuid import uuid4

from blueOcean.counter_repository import RedisCounterRepository
from blueOcean.counter_worker import run_counter


class CounterProcessManager:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._repository = RedisCounterRepository(redis_url)
        self._processes: dict[str, Process] = {}
        self._lock = Lock()
        self._repository.ping()

    def create(self) -> str:
        counter_id = uuid4().hex[:8]
        self._repository.create(counter_id)
        self._launch(counter_id)
        return counter_id

    def start(self, counter_id: str) -> None:
        with self._lock:
            current = self._processes.get(counter_id)
            if current is not None and current.is_alive():
                return
            if current is not None:
                current.join()
            if not self._repository.prepare_start(counter_id):
                return
            self._launch_unlocked(counter_id)

    def _launch(self, counter_id: str) -> None:
        with self._lock:
            self._launch_unlocked(counter_id)

    def _launch_unlocked(self, counter_id: str) -> None:
        process = Process(
            target=run_counter,
            args=(self._redis_url, counter_id),
            name=f"counter-{counter_id}",
        )
        process.start()
        self._processes[counter_id] = process

    def stop(self, counter_id: str) -> None:
        self._repository.request_stop(counter_id)
        with self._lock:
            process = self._processes.get(counter_id)
            if process is None or not process.is_alive():
                return
            process.join(timeout=3)
            if process.is_alive():
                process.terminate()
                process.join()
                self._repository.mark_stopped(counter_id)

    def delete(self, counter_id: str) -> None:
        self.stop(counter_id)
        self._repository.delete(counter_id)
        with self._lock:
            self._processes.pop(counter_id, None)

    def snapshot(self) -> list[dict]:
        return self._repository.list()

    def shutdown(self) -> None:
        with self._lock:
            counter_ids = list(self._processes)
        for counter_id in counter_ids:
            self.stop(counter_id)
