from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any

from cuid2 import Cuid

from blueOcean.domain.ohlcv import Timeframe


@dataclass
class Bot:
    id: BotId
    status: BotStatus
    context: BotContext
    worker: IBotWorker | None
    pid: int | None
    started_at: datetime | None
    finished_at: datetime | None
    label: str | None

    @classmethod
    def create(cls, context: BotContext):
        return Bot(
            id=BotId.create(),
            status=BotStatus.NONE,
            context=context,
            worker=None,
            pid=None,
            started_at=None,
            finished_at=None,
            label=None,
        )

    def attach(self, worker: IBotWorker):
        self.worker = worker

    def rename(self, name: str):
        self.label = name

    def start(self):
        self.worker.launch()
        self.pid = getattr(self.worker, "pid", None)
        self.started_at = datetime.now()
        self.status = BotStatus.RUNNING

    def stop(self):
        self.worker.shutdown()
        self.pid = None
        self.finished_at = datetime.now()
        self.status = BotStatus.STOPPED


# region value_objects


class BotRunMode(IntEnum):
    BACKTEST = 2


class BotStatus(IntEnum):
    NONE = 0
    STOPPED = 1
    RUNNING = 2


@dataclass(frozen=True)
class BotId:
    value: str

    @classmethod
    def create(cls) -> BotId:
        return cls(Cuid().generate())


@dataclass(frozen=True)
class BotContext(metaclass=ABCMeta):
    strategy_cls: type
    strategy_args: dict[str, Any]
    source: str
    symbol: str
    timeframe: Timeframe

    @property
    @abstractmethod
    def mode(self) -> BotRunMode:
        raise NotImplementedError()


@dataclass(frozen=True)
class BacktestContext(BotContext):
    start_at: datetime
    end_at: datetime

    @property
    def mode(self):
        return BotRunMode.BACKTEST


# region interfaces


class IBotWorker(metaclass=ABCMeta):
    @abstractmethod
    def launch(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def shutdown(self) -> None:
        raise NotImplementedError()


class IBotWorkerFactory(metaclass=ABCMeta):
    @abstractmethod
    def create(self, id: BotId, context: BotContext) -> IBotWorker:
        raise NotImplementedError()


class IBotRepository(metaclass=ABCMeta):
    @abstractmethod
    def get_all(self) -> list[Bot]:
        raise NotImplementedError()

    @abstractmethod
    def find_by_id(self, id: BotId) -> Bot:
        raise NotImplementedError()
    
    @abstractmethod
    def find_by_ids(self, *ids: BotId) -> list[Bot]:
        raise NotImplementedError()

    @abstractmethod
    def save(self, bot: Bot) -> Bot:
        raise NotImplementedError()
