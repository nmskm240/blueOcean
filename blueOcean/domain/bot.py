from __future__ import annotations

from abc import ABCMeta
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any

from blueOcean.domain.account import AccountId
from blueOcean.domain.ohlcv import Timeframe


@dataclass
class Bot:
    id: BotId
    status: BotStatus
    context: BotContext
    started_at: datetime
    finished_at: datetime | None
    label: str | None

    @property
    def mode(self) -> BotRunMode:
        return (
            BotRunMode.LIVE
            if isinstance(self.context, LiveContext)
            else BotRunMode.BACKTEST
        )

    def rename(self, name: str):
        self.label = name

    def start(self):
        self.started_at = datetime.now()
        self.status = BotStatus.RUNNING

    def stop(self):
        self.finished_at = datetime.now()
        self.status = BotStatus.STOPPED


# region value_objects


class BotRunMode(IntEnum):
    LIVE = 1
    BACKTEST = 2


class BotStatus(IntEnum):
    STOPPED = 0
    RUNNING = 1


@dataclass(frozen=True)
class BotId:
    value: str | None

    @classmethod
    def empty(cls) -> BotId:
        return cls(value=None)

    @property
    def is_empty(self) -> bool:
        return self.value is None


@dataclass(frozen=True)
class BotContext(metaclass=ABCMeta):
    strategy_name: str
    strategy_args: dict[str, Any]
    source: str
    symbol: str
    timeframe: Timeframe


@dataclass(frozen=True)
class LiveContext(BotContext):
    account_id: AccountId
    pid: int


@dataclass(frozen=True)
class BacktestContext(BotContext):
    start_at: datetime
    end_at: datetime
