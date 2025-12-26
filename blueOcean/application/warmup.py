from __future__ import annotations

import threading


class WarmupState:
    def __init__(self) -> None:
        self._ready = threading.Event()

    def mark_ready(self) -> None:
        self._ready.set()

    def mark_pending(self) -> None:
        self._ready.clear()

    def is_ready(self) -> bool:
        return self._ready.is_set()
