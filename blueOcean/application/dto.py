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

    def to_metadata(self) -> dict[str, Any]:
        return {
            "run_type": "bot",
            "symbol": self.symbol,
            "compression": self.compression,
            "account_id": self.account_id,
        }


@dataclass
class BacktestConfig:
    symbol: str
    source: str
    compression: int
    strategy_cls: Type[bt.Strategy]
    strategy_args: dict[str, Any]
    cash: int
    time_range: DatetimeRange

    def to_metadata(self) -> dict[str, Any]:
        return {
            "run_type": "backtest",
            "symbol": self.symbol,
            "source": self.source,
            "compression": self.compression,
            "time_range": {
                "start_at": self.time_range.start_at.isoformat(),
                "end_at": self.time_range.end_at.isoformat(),
            },
        }


@dataclass(frozen=True)
class DatetimeRange:
    start_at: datetime
    end_at: datetime

    def between(self, date: datetime):
        return self.start_at <= date < self.end_at
