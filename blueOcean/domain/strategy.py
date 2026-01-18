from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar

import backtrader as bt
from cuid2 import Cuid

StrategyType = TypeVar("StrategyType", bound=bt.Strategy)
ParameterType = str | int | float | bool
StrategyArgs = dict[str, ParameterType]


@dataclass
class StrategySnapshot:
    id: StrategySnapshotId = field(default_factory=lambda: StrategySnapshotId())
    name: str = field(default="")


@dataclass(frozen=True)
class StrategySnapshotId:
    value: str = field(default_factory=Cuid().generate)


@dataclass(frozen=True)
class Parameter:
    name: str
    value_type: ParameterType
    default: ParameterType | None = None


# region interfaces


class IStrategySnapshotRepository(metaclass=ABCMeta):
    @abstractmethod
    def find_by_id(self, id: StrategySnapshotId) -> StrategySnapshot:
        raise NotImplementedError()

    @abstractmethod
    def find_by_ids(self, *ids: StrategySnapshotId) -> list[StrategySnapshot]:
        raise NotImplementedError()

    @abstractmethod
    def save(self, snapshot: StrategySnapshot) -> StrategySnapshot:
        raise NotImplementedError()
