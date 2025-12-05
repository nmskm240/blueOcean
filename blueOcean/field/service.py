import time
from datetime import UTC, datetime, timedelta
from multiprocessing import Process, Queue
from typing import Type, TypeVar

import backtrader as bt

from blueOcean.logging import logger
from blueOcean.ohlcv import OhlcvFetcher

TStrategy = TypeVar("TStrategy", bound=bt.Strategy)


class StrategyRunner:
    def __init__(self):
        self._analyzers: list[tuple[type, str, dict]] = []

    def add_analyzer(self, analyzer_cls: type, name: str | None = None, **kwargs):
        self._analyzers.append((analyzer_cls, name, kwargs))
        return self

    def run(
        self, strategy: Type[TStrategy], datafeed: bt.feed.DataBase, **strategy_args
    ) -> tuple[TStrategy, bt.Cerebro]:
        cerebro = bt.Cerebro()
        cerebro.adddata(datafeed)
        cerebro.broker.setcash(10_000)
        cerebro.broker.setcommission(leverage=3)
        cerebro.addsizer(bt.sizers.FixedSize, stake=0.1)
        cerebro.addstrategy(strategy, **strategy_args)

        for analyzer_cls, name, kwargs in self._analyzers:
            if name:
                cerebro.addanalyzer(analyzer_cls, _name=name, **kwargs)
            else:
                cerebro.addanalyzer(analyzer_cls, **kwargs)

        result = cerebro.run()[0]
        returns = result.analyzers.timereturn.get_analysis()

        return result, cerebro


class ExchangeWorker(Process):
    def __init__(
        self,
        fetcher: OhlcvFetcher,
        symbol: str,
    ):
        super().__init__()
        self.queue = Queue()
        self.symbol = symbol
        self._fetcher = fetcher
        self.name = f"{self._fetcher.source}:{self.symbol}"

    def run(self):
        while True:
            now = datetime.now(tz=UTC)
            next_min = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            # MEMO: since_atの時間が含まれないことを考慮するため2分前の時間でリクエストを行う
            since_at = next_min - timedelta(minutes=2)
            sleep_time = (next_min - now).total_seconds()
            time.sleep(sleep_time)

            for batch in self._fetcher.fetch_ohlcv(self.symbol, since_at=since_at):
                for ohlcv in batch:
                    if now < ohlcv.time:
                        continue
                    self.queue.put(ohlcv)
