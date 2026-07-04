from dataclasses import dataclass
from multiprocessing import Event, Process, Value
from multiprocessing.synchronize import Event as EventType
from threading import Lock
from typing import Any
from uuid import uuid4

from blueOcean.counter_worker import run_counter


@dataclass
class CounterJob:
    id: str
    value: Any
    process: Process | None = None
    stop_event: EventType | None = None


class CounterProcessManager:
    def __init__(self) -> None:
        self._jobs: dict[str, CounterJob] = {}
        self._lock = Lock()

    def create(self) -> str:
        counter_id = uuid4().hex[:8]
        with self._lock:
            self._jobs[counter_id] = CounterJob(counter_id, Value("Q", 0))
        self.start(counter_id)
        return counter_id

    def start(self, counter_id: str) -> None:
        with self._lock:
            job = self._jobs.get(counter_id)
            if job is None:
                return
            if job.process is not None and job.process.is_alive():
                return
            if job.process is not None:
                job.process.join()

            with job.value.get_lock():
                job.value.value = 0

            job.stop_event = Event()
            job.process = Process(
                target=run_counter,
                args=(job.stop_event, job.value, counter_id),
                name=f"counter-{counter_id}",
            )
            job.process.start()

    def stop(self, counter_id: str) -> None:
        with self._lock:
            job = self._jobs.get(counter_id)
            if job is None or job.process is None or not job.process.is_alive():
                return

            job.stop_event.set()
            job.process.join(timeout=3)
            if job.process.is_alive():
                job.process.terminate()
                job.process.join()

    def delete(self, counter_id: str) -> None:
        self.stop(counter_id)
        with self._lock:
            self._jobs.pop(counter_id, None)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": job.id,
                    "count": job.value.value,
                    "is_alive": job.process is not None and job.process.is_alive(),
                    "pid": job.process.pid if job.process is not None else None,
                }
                for job in self._jobs.values()
            ]

    def shutdown(self) -> None:
        with self._lock:
            counter_ids = list(self._jobs)
        for counter_id in counter_ids:
            self.stop(counter_id)
