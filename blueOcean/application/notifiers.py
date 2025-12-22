from dataclasses import replace
from datetime import datetime
from types import MappingProxyType
from typing import Type

from blueOcean.application import usecases
from blueOcean.application.dto import BacktestConfig
from blueOcean.domain.ohlcv import Timeframe


class BacktestNotifier:
    def __init__(self):
        self._state = BacktestConfig()

    @property
    def source(self):
        return self._state.source

    @source.setter
    def source(self, source: str):
        self._state.source = source

    @property
    def symbol(self):
        return self._state.symbol

    @symbol.setter
    def symbol(self, symbol: str):
        self._state.symbol = symbol

    @property
    def timeframe(self):
        return self._state.timeframe

    @timeframe.setter
    def timeframe(self, timeframe: Timeframe):
        self._state.timeframe = timeframe

    @property
    def strategy_cls(self):
        return self._state.strategy_cls

    @strategy_cls.setter
    def strategy_cls(self, strategy_cls: Type):
        self._state.strategy_cls = strategy_cls

    @property
    def strategy_args(self):
        return MappingProxyType(self._state.strategy_args)

    @strategy_args.setter
    def strategy_args(self, strategy_args: dict):
        self._state.strategy_args = strategy_args

    @property
    def start_at(self):
        return self._state.time_range.start_at

    @start_at.setter
    def start_at(self, start_at: datetime):
        self._state.time_range = replace(self._state.time_range, start_at=start_at)

    @property
    def end_at(self):
        return self._state.time_range.end_at

    @end_at.setter
    def end_at(self, end_at: datetime):
        self._state.time_range = replace(self._state.time_range, end_at=end_at)

    def on_request_backtest(self):
        usecases.run_bot(self._state)
