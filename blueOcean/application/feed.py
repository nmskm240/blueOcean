from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from queue import Empty, Queue

import backtrader as bt
from injector import inject

from blueOcean.application.warmup import WarmupState
from blueOcean.domain.ohlcv import Ohlcv, OhlcvFetcher, Timeframe

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

    params = (
        ("fetcher", None),
        ("symbol", None),
        ("ohlcv_timeframe", Timeframe.ONE_MINUTE),
        ("warmup_limit", 1000),
        ("timeframe", bt.TimeFrame.NoTimeFrame),
    )

    @inject
    def __init__(
        self,
        queue: Queue,
        fetcher: OhlcvFetcher | None = None,
        symbol: str | None = None,
        ohlcv_timeframe: Timeframe = Timeframe.ONE_MINUTE,
        warmup_state: WarmupState | None = None,
        warmup_limit: int = 1000,
    ):
        super().__init__()
        self.queue = queue
        self.p.fetcher = fetcher
        self.p.symbol = symbol
        self.p.ohlcv_timeframe = ohlcv_timeframe
        self.p.warmup_limit = warmup_limit
        self.p.timeframe = self.p.ohlcv_timeframe.to_backtrade()
        self.p.compression = 1
        self._warmup_state = warmup_state or WarmupState()
        if warmup_state is None:
            self._warmup_state.mark_ready()
        self._warmup_data: deque[Ohlcv] = deque()
        self._warmup_ready_pending = False

    def islive(self):
        return True

    def start(self):
        super().start()
        self._prepare_warmup()

    def _load(self):
        if self._warmup_ready_pending:
            self._warmup_ready_pending = False
            self._warmup_state.mark_ready()

        if self._warmup_data:
            tick = self._warmup_data.popleft()
            if not self._warmup_data:
                self._warmup_ready_pending = True
            self._set_tick(tick)
            return True

        try:
            tick = self.queue.get(timeout=1)
        except Empty:
            return None

        self._set_tick(tick)
        return True

    def _prepare_warmup(self) -> None:
        if self.p.fetcher is None or self.p.symbol is None:
            self._warmup_state.mark_ready()
            return

        warmup_limit = max(int(self.p.warmup_limit), 0)
        if warmup_limit == 0:
            self._warmup_state.mark_ready()
            return

        self._warmup_state = self._warmup_state or WarmupState()
        self._warmup_state.mark_pending()

        now = datetime.now(tz=UTC)
        since_at = now - timedelta(minutes=warmup_limit * int(self.p.ohlcv_timeframe))
        history: list[Ohlcv] = []
        for batch in self.p.fetcher.fetch_ohlcv(self.p.symbol, since_at=since_at):
            history.extend([ohlcv for ohlcv in batch if ohlcv.time <= now])

        if not history:
            self._warmup_state.mark_ready()
            return

        self._warmup_data = deque(history[-warmup_limit:])

    def _set_tick(self, tick: Ohlcv) -> None:
        dt_value = tick.time
        if hasattr(dt_value, "to_pydatetime"):
            dt_value = dt_value.to_pydatetime()
        if dt_value.tzinfo is not None:
            dt_value = dt_value.replace(tzinfo=None)

        self.lines.datetime[0] = bt.date2num(dt_value)
        self.lines.close[0] = tick.close
        self.lines.open[0] = tick.open
        self.lines.high[0] = tick.high
        self.lines.low[0] = tick.low
        self.lines.volume[0] = tick.volume
        self.lines.openinterest[0] = 0.0
