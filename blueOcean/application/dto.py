from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Type

import backtrader as bt


@dataclass
class BotConfig:
    account_id: str
    symbol: str
    compression: int
    strategy_cls: Type[bt.Strategy]
    strategy_args: dict[str, Any]


@dataclass
class BacktestConfig:
    symbol: str
    source: str
    compression: int
    strategy_cls: Type[bt.Strategy]
    strategy_args: dict[str, Any]
    cash: int
    time_range: DatetimeRange


@dataclass(frozen=True)
class DatetimeRange:
    start_at: datetime
    end_at: datetime

    def between(self, date: datetime):
        return self.start_at <= date < self.end_at
