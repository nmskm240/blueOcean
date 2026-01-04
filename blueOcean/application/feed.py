from __future__ import annotations

from queue import Empty, Queue

import backtrader as bt
from injector import inject


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
