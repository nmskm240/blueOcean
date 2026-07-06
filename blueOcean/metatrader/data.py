from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import backtrader as bt


_TIMEFRAMES = {
    (bt.TimeFrame.Minutes, 1): "M1",
    (bt.TimeFrame.Minutes, 2): "M2",
    (bt.TimeFrame.Minutes, 3): "M3",
    (bt.TimeFrame.Minutes, 5): "M5",
    (bt.TimeFrame.Minutes, 10): "M10",
    (bt.TimeFrame.Minutes, 15): "M15",
    (bt.TimeFrame.Minutes, 30): "M30",
    (bt.TimeFrame.Minutes, 60): "H1",
    (bt.TimeFrame.Minutes, 120): "H2",
    (bt.TimeFrame.Minutes, 240): "H4",
    (bt.TimeFrame.Days, 1): "D1",
    (bt.TimeFrame.Weeks, 1): "W1",
    (bt.TimeFrame.Months, 1): "MN1",
}


def _value(row: Any, name: str) -> Any:
    try:
        return row[name]
    except (KeyError, TypeError, IndexError):
        return getattr(row, name)


class MT5Data(bt.feed.DataBase):
    """Historical-then-live OHLCV feed backed by MT5 ``copy_rates_from_pos``."""

    params = (
        ("store", None),
        ("symbol", None),
        ("history", 500),
        ("poll_interval", 1.0),
        ("live", True),
    )

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self._store = self.p.store
        if self._store is None:
            raise ValueError("MT5Data requires store=MT5Store(...)")
        self._symbol = self.p.symbol or self.p.dataname
        if not self._symbol:
            raise ValueError("MT5Data requires symbol or dataname")
        self._rows: list[Any] = []
        self._last_time = 0
        self._next_poll = 0.0
        self._timeframe = 0

    def islive(self) -> bool:
        return bool(self.p.live)

    def start(self) -> None:
        super().start()
        self._store.start()
        self._store.client.ensure_symbol(self._symbol)
        key = (self.p.timeframe, self.p.compression)
        if key not in _TIMEFRAMES:
            raise ValueError(f"Unsupported Backtrader timeframe/compression: {key}")
        self._timeframe = self._store.client.timeframe(_TIMEFRAMES[key])
        rates = self._store.client.copy_rates_from_pos(
            self._symbol, self._timeframe, 1, self.p.history
        )
        if rates is None:
            raise RuntimeError(f"MT5 rate request failed: {self._store.client.last_error()}")
        self._rows.extend(sorted(rates, key=lambda row: _value(row, "time")))
        self.put_notification(self.DELAYED)

    def stop(self) -> None:
        self._store.stop()
        super().stop()

    def _load(self):
        while self._rows:
            row = self._rows.pop(0)
            timestamp = int(_value(row, "time"))
            if timestamp <= self._last_time:
                continue
            self._last_time = timestamp
            self.lines.datetime[0] = bt.date2num(datetime.fromtimestamp(timestamp, timezone.utc))
            self.lines.open[0] = float(_value(row, "open"))
            self.lines.high[0] = float(_value(row, "high"))
            self.lines.low[0] = float(_value(row, "low"))
            self.lines.close[0] = float(_value(row, "close"))
            self.lines.volume[0] = float(_value(row, "tick_volume"))
            self.lines.openinterest[0] = 0.0
            return True

        if not self.p.live:
            return False
        now = time.monotonic()
        if now < self._next_poll:
            return None
        self._next_poll = now + self.p.poll_interval
        # Position 0 is the still-forming candle. Emit only completed candles so
        # that a Backtrader bar never silently changes after ``next`` ran.
        rates = self._store.client.copy_rates_from_pos(self._symbol, self._timeframe, 1, 1)
        if rates is None:
            return None
        self._rows.extend(sorted(rates, key=lambda row: _value(row, "time")))
        if self._rows:
            self.put_notification(self.LIVE)
        return self._load()
