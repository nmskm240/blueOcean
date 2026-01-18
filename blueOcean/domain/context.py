from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from cuid2 import Cuid

from blueOcean.domain.ohlcv import Timeframe
from blueOcean.domain.session import SessionId
from blueOcean.domain.strategy import StrategyArgs, StrategySnapshotId


@dataclass
class Context:
    id: ContextId = field(default_factory=lambda: ContextId())
    strategy_snapshot_id: StrategySnapshotId = field(
        default_factory=lambda: StrategySnapshotId()
    )
    strategy_args: StrategyArgs = field(default_factory=dict)
    source: str = field(default="")
    symbol: str = field(default="")
    timeframe: Timeframe = field(default=Timeframe.ONE_MINUTE)

    start_at: datetime = field(default=datetime.min)
    end_at: datetime = field(default=datetime.max)


# region value_objects


@dataclass(frozen=True)
class ContextId:
    value: str = field(default_factory=Cuid().generate)


# region interfaces


class IContextRepository(metaclass=ABCMeta):
    @abstractmethod
    def find_by_id(self, id: ContextId) -> Context:
        raise NotImplementedError()

    @abstractmethod
    def find_by_ids(self, *ids: ContextId) -> list[Context]:
        raise NotImplementedError()

    @abstractmethod
    def find_by_session_id(self, session_id: SessionId) -> list[Context]:
        raise NotImplementedError()

    @abstractmethod
    def save(self, context: Context) -> Context:
        raise NotImplementedError()
