from __future__ import annotations

from threading import RLock
from typing import Any

from .client import MT5Client


class MT5Store:
    """Owns one MT5 terminal connection shared by feeds and broker."""

    def __init__(self, client: MT5Client | None = None, **connection: Any) -> None:
        self.client = client or MT5Client(**connection)
        self._users = 0
        self._lock = RLock()

    def start(self) -> None:
        with self._lock:
            if self._users == 0:
                self.client.connect()
            self._users += 1

    def stop(self) -> None:
        with self._lock:
            if self._users == 0:
                return
            self._users -= 1
            if self._users == 0:
                self.client.shutdown()

    def getdata(self, **kwargs):
        from .data import MT5Data

        return MT5Data(store=self, **kwargs)

    def getbroker(self, **kwargs):
        from .broker import MT5Broker

        return MT5Broker(store=self, **kwargs)
