from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Type

import backtrader as bt

from blueOcean.domain.account import AccountId
from blueOcean.domain.bot import BacktestContext, LiveContext
from blueOcean.domain.ohlcv import Timeframe


@dataclass(frozen=True)
class DatetimeRange:
    start_at: datetime = field(default=datetime.min)
    end_at: datetime = field(default=datetime.max)

    def between(self, date: datetime):
        return self.start_at <= date < self.end_at


@dataclass
class IBotConfig[TContext](metaclass=ABCMeta):
    source: str = field(default="")
    symbol: str = field(default="")
    timeframe: Timeframe = field(default=Timeframe.ONE_MINUTE)
    strategy_cls: Type[bt.Strategy] = field(default=None)
    strategy_args: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def to_context(self) -> TContext:
        raise NotImplementedError()


@dataclass
class LiveConfig(IBotConfig[LiveContext]):
    account_id: str = field(default="")

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
    cash: int = field(default=10000)
    time_range: DatetimeRange = field(default_factory=DatetimeRange)

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
class AccountCredentialInfo:
    account_id: str = field(default="")
    exchange_name: str = field(default="")
    api_key: str = field(default="")
    api_secret: str = field(default="")
    is_sandbox: bool = field(default=True)
    label: str = field(default="")


@dataclass(frozen=True)
class BotInfo:
    bot_id: str
    label: str
    status: str
    mode: str
    source: str
    symbol: str
    timeframe: Timeframe
    strategy: str
    started_at: datetime | None
    finished_at: datetime | None
