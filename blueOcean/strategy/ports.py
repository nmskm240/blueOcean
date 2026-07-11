from typing import Protocol

import backtrader as bt

from blueOcean.strategy.models import StrategyConfig


class MarketDataSource(Protocol):
    def create_feed(self, config: StrategyConfig, stop_event, status_queue) -> bt.feed.DataBase: ...


class ExecutionBackend(Protocol):
    def configure(self, cerebro: bt.Cerebro, config: StrategyConfig) -> None: ...

    def result(self, cerebro: bt.Cerebro, strategies: list) -> dict: ...
