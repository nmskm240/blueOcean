from __future__ import annotations

from datetime import UTC, datetime
from queue import Empty, Queue

import backtrader as bt
from injector import inject

from blueOcean.domain.ohlcv import Timeframe

class LocalDataFeed(bt.feed.DataBase):
    lines = ("datetime", "open", "high", "low", "close", "volume", "openinterest")

    params = (
        ("repository", None),
        ("symbol", None),
        ("source", None),
        ("ohlcv_timeframe", Timeframe.ONE_MINUTE),
        ("start_at", datetime.min),
        ("end_at", datetime.max),
        # Feed内部のtimeframe用
        ("timeframe", bt.TimeFrame.NoTimeFrame),
    )

    def __init__(self):
        super().__init__()
        self._data_iter = None
        # NOTE: timeframeとcompressionをAnalyzerなどが利用するため明示が必要
        self.p.timeframe = self.p.ohlcv_timeframe.to_backtrade()
        self.p.compression = 1

    def start(self):
        super().start()

        ohlcvs = self.p.repository.find(
            symbol=self.p.symbol,
            source=self.p.source,
            timeframe=self.p.ohlcv_timeframe,
            start_date=self.p.start_at,
            end_date=self.p.end_at,
        )

        self._data_iter = iter(
            [(o.time, o.open, o.high, o.low, o.close, o.volume) for o in ohlcvs]
        )

    def _load(self):
        if self._data_iter is None:
            return False

        try:
            dt_, o, h, l, c, v = next(self._data_iter)
        except StopIteration:
            return False

        if hasattr(dt_, "to_pydatetime"):
            dt_ = dt_.to_pydatetime()
        if dt_.tzinfo is not None:
            dt_ = dt_.replace(tzinfo=None)

        self.lines.datetime[0] = bt.date2num(dt_)
        self.lines.open[0] = o
        self.lines.high[0] = h
        self.lines.low[0] = l
        self.lines.close[0] = c
        self.lines.volume[0] = v
        self.lines.openinterest[0] = 0.0

        return True


# TODO: Feed内でFetcherを動かすほうが考えること少なくなってよさそう
class QueueDataFeed(bt.feed.DataBase):
    lines = (
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "openinterest",
    )

    @inject
    def __init__(self):
        super().__init__()
        self.queue = Queue()

    def islive(self):
        return True

    def _load(self):
        try:
            tick = self.queue.get(timeout=1)
        except Empty:
            return None

        self.lines.datetime[0] = bt.date2num(tick.time)
        self.lines.close[0] = tick.close
        self.lines.open[0] = tick.open
        self.lines.high[0] = tick.high
        self.lines.low[0] = tick.low
        self.lines.volume[0] = tick.volume
        self.lines.openinterest[0] = 0.0

        return True