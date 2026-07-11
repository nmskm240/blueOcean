from __future__ import annotations

import multiprocessing
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from queue import Empty
from threading import RLock, Thread

from blueOcean.strategy.models import StrategyAlreadyRunningError, StrategyRun
from blueOcean.strategy.repositories import StrategyRepository, StrategyRunRepository


def run_dummy_strategy(stop_event, status_queue) -> None:
    status_queue.put(("running", datetime.now(timezone.utc)))
    while not stop_event.wait(1.0):
        status_queue.put(("heartbeat", datetime.now(timezone.utc)))


@dataclass
class RunHandle:
    process: object
    stop_event: object
    status_queue: object


class StrategySupervisor:
    def __init__(
        self,
        strategies: StrategyRepository,
        runs: StrategyRunRepository,
        context=None,
    ) -> None:
        self._strategies = strategies
        self._runs = runs
        self._context = context or multiprocessing.get_context("spawn")
        self._handles: dict[str, RunHandle] = {}
        self._lock = RLock()

    def reconcile(self) -> None:
        self._runs.mark_active_lost()

    def start(self, strategy_id: str) -> StrategyRun:
        with self._lock:
            self._strategies.get(strategy_id)
            if self._runs.active_for_strategy(strategy_id) is not None:
                raise StrategyAlreadyRunningError("この戦略は既に稼働しています")
            stop_event = self._context.Event()
            status_queue = self._context.Queue()
            process = self._context.Process(
                target=run_dummy_strategy,
                args=(stop_event, status_queue),
                name=f"blueocean-strategy-{strategy_id}",
                daemon=True,
            )
            process.start()
            run = self._runs.save(StrategyRun(strategy_id=strategy_id, pid=process.pid))
            self._handles[run.id] = RunHandle(process, stop_event, status_queue)
            Thread(target=self._monitor, args=(run.id,), daemon=True).start()
            return run

    def stop(self, run_id: str) -> StrategyRun:
        with self._lock:
            run = self._runs.get(run_id)
            handle = self._handles.get(run_id)
            if handle is not None:
                handle.stop_event.set()
                handle.process.join(5.0)
                if handle.process.is_alive():
                    handle.process.terminate()
                    handle.process.join(1.0)
                self._handles.pop(run_id, None)
            return self._runs.save(
                replace(
                    run,
                    state="stopped",
                    pid=None,
                    stopped_at=datetime.now(timezone.utc),
                )
            )

    def stop_all(self) -> None:
        for run_id in list(self._handles):
            self.stop(run_id)

    def _monitor(self, run_id: str) -> None:
        while True:
            with self._lock:
                handle = self._handles.get(run_id)
            if handle is None:
                return
            try:
                event, occurred_at = handle.status_queue.get(timeout=1.5)
            except Empty:
                if not handle.process.is_alive():
                    with self._lock:
                        run = self._runs.get(run_id)
                        self._runs.save(
                            replace(
                                run,
                                state="error",
                                pid=None,
                                error=f"Strategy process exited with code {handle.process.exitcode}",
                                stopped_at=datetime.now(timezone.utc),
                            )
                        )
                        self._handles.pop(run_id, None)
                    return
                continue
            run = self._runs.get(run_id)
            if event == "running":
                self._runs.save(replace(run, state="running", heartbeat_at=occurred_at))
            elif event == "heartbeat":
                self._runs.save(replace(run, heartbeat_at=occurred_at))
