from __future__ import annotations

import multiprocessing
import os
import subprocess
from dataclasses import dataclass
from queue import Empty
from threading import RLock, Thread
from typing import Any


@dataclass(frozen=True)
class WorkerStatus:
    state: str
    pid: int | None = None
    error: str | None = None


def _matching_terminal_pids(path: str | None) -> set[int]:
    """Return PIDs whose executable is the configured terminal path."""
    if os.name != "nt" or not path:
        return set()
    env = os.environ.copy()
    env["BLUEOCEAN_MT5_PATH"] = os.path.normcase(os.path.abspath(path))
    script = (
        "$target = $env:BLUEOCEAN_MT5_PATH; "
        "Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | "
        "Where-Object { $_.ExecutablePath -and "
        "([System.IO.Path]::GetFullPath($_.ExecutablePath).ToLowerInvariant() -eq $target.ToLowerInvariant()) } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {int(line) for line in result.stdout.splitlines() if line.strip().isdigit()}


def _terminate_terminal_pids(pids: set[int]) -> None:
    """Terminate only MT5 processes started for this worker."""
    if os.name != "nt":
        return
    for pid in pids:
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def run_mt5_worker(connection: dict[str, Any], stop_event, status_queue) -> None:
    """Own one MT5 connection until the web process asks it to stop."""
    from .client import MT5Client

    client = None
    terminal_path = connection.get("path")
    existing_terminal_pids = _matching_terminal_pids(terminal_path)
    try:
        client = MT5Client(**connection)
        client.connect()
        account = client.account_info()
        if account is None:
            raise RuntimeError(f"MT5 account_info failed: {client.last_error()}")
        status_queue.put(("running", None))
        stop_event.wait()
    except Exception as exc:
        status_queue.put(("error", str(exc)))
    finally:
        if client is not None:
            try:
                client.shutdown()
            except Exception:
                pass
        owned_terminal_pids = _matching_terminal_pids(terminal_path) - existing_terminal_pids
        _terminate_terminal_pids(owned_terminal_pids)


@dataclass
class _WorkerHandle:
    process: Any
    stop_event: Any
    status_queue: Any
    terminal_path: str | None = None
    existing_terminal_pids: set[int] | None = None
    state: str = "starting"
    error: str | None = None


class MT5WorkerManager:
    """Starts and stops one isolated MT5 connection process per account."""

    def __init__(
        self,
        context=None,
        terminal_pids=None,
        terminate_terminals=None,
        startup_timeout: float | None = 30.0,
    ) -> None:
        self._context = context or multiprocessing.get_context("spawn")
        self._terminal_pids = terminal_pids or _matching_terminal_pids
        self._terminate_terminals = terminate_terminals or _terminate_terminal_pids
        self._startup_timeout = startup_timeout
        self._workers: dict[str, _WorkerHandle] = {}
        self._lock = RLock()

    def start(self, account_id: str, connection: dict[str, Any]) -> WorkerStatus:
        with self._lock:
            current = self._workers.get(account_id)
            if current is not None and current.process.is_alive():
                return self._status(current)
            if current is not None:
                self._workers.pop(account_id, None)

            stop_event = self._context.Event()
            status_queue = self._context.Queue()
            terminal_path = connection.get("path")
            existing_terminal_pids = self._terminal_pids(terminal_path)
            process = self._context.Process(
                target=run_mt5_worker,
                args=(connection, stop_event, status_queue),
                name=f"blueocean-mt5-{account_id}",
                daemon=True,
            )
            handle = _WorkerHandle(
                process,
                stop_event,
                status_queue,
                terminal_path,
                existing_terminal_pids,
            )
            self._workers[account_id] = handle
            try:
                process.start()
            except Exception:
                self._workers.pop(account_id, None)
                raise
            if self._startup_timeout is not None:
                Thread(
                    target=self._watch_startup,
                    args=(account_id, handle),
                    name=f"blueocean-mt5-watch-{account_id}",
                    daemon=True,
                ).start()
            return self._status(handle)

    def _watch_startup(self, account_id: str, handle: _WorkerHandle) -> None:
        handle.process.join(self._startup_timeout)
        with self._lock:
            if self._workers.get(account_id) is not handle:
                return
            self._drain(handle)
            if handle.state != "starting":
                return
            if handle.process.is_alive():
                handle.process.terminate()
                handle.process.join(1.0)
            owned_terminal_pids = self._terminal_pids(handle.terminal_path) - (
                handle.existing_terminal_pids or set()
            )
            self._terminate_terminals(owned_terminal_pids)
            handle.state = "error"
            handle.error = f"MT5 startup timed out after {self._startup_timeout:g} seconds"

    def stop(self, account_id: str, timeout: float = 5.0) -> WorkerStatus:
        with self._lock:
            handle = self._workers.get(account_id)
            if handle is None:
                return WorkerStatus("stopped")
            handle.stop_event.set()
            handle.process.join(timeout)
            if handle.process.is_alive():
                handle.process.terminate()
                handle.process.join(1.0)
            owned_terminal_pids = self._terminal_pids(handle.terminal_path) - (
                handle.existing_terminal_pids or set()
            )
            self._terminate_terminals(owned_terminal_pids)
            self._workers.pop(account_id, None)
            return WorkerStatus("stopped")

    def get_status(self, account_id: str) -> WorkerStatus:
        with self._lock:
            handle = self._workers.get(account_id)
            if handle is None:
                return WorkerStatus("stopped")
            return self._status(handle)

    def get_statuses(self) -> dict[str, WorkerStatus]:
        with self._lock:
            return {account_id: self._status(handle) for account_id, handle in self._workers.items()}

    def stop_all(self) -> None:
        for account_id in list(self._workers):
            self.stop(account_id)

    @staticmethod
    def _drain(handle: _WorkerHandle) -> None:
        while True:
            try:
                handle.state, handle.error = handle.status_queue.get_nowait()
            except Empty:
                break

    def _status(self, handle: _WorkerHandle) -> WorkerStatus:
        self._drain(handle)
        is_alive = handle.process.is_alive()
        if not is_alive and handle.state != "error":
            handle.state = "error" if handle.process.exitcode not in (None, 0) else "stopped"
            if handle.state == "error" and not handle.error:
                handle.error = f"Worker exited with code {handle.process.exitcode}"
        return WorkerStatus(handle.state, handle.process.pid if is_alive else None, handle.error)
