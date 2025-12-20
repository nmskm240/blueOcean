from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Type

import backtrader as bt

from blueOcean.domain.account import AccountId
from blueOcean.domain.bot import BacktestContext, LiveContext
from blueOcean.domain.ohlcv import Timeframe


@dataclass
class IBotConfig[TContext](metaclass=ABCMeta):
    source: str
    symbol: str
    timeframe: Timeframe
    strategy_cls: Type[bt.Strategy]
    strategy_args: dict[str, Any]

    @abstractmethod
    def to_context(self) -> TContext:
        raise NotImplementedError()


@dataclass
class LiveConfig(IBotConfig[LiveContext]):
    account_id: str

    def to_context(self):
        return LiveContext(
            strategy_cls=self.strategy_cls,
            strategy_args=self.strategy_args,
            source=self.source,
            symbol=self.symbol,
            timeframe=self.timeframe,
            account_id=AccountId(self.account_id),
        )


@dataclass
class BacktestConfig(IBotConfig[BacktestContext]):
    cash: int
    time_range: DatetimeRange

    def to_context(self):
        return BacktestContext(
            strategy_cls=self.strategy_cls,
            strategy_args=self.strategy_args,
            source=self.source,
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_at=self.time_range.start_at,
            end_at=self.time_range.end_at,
        )


@dataclass(frozen=True)
class DatetimeRange:
    start_at: datetime
    end_at: datetime

    def between(self, date: datetime):
        return self.start_at <= date < self.end_at
