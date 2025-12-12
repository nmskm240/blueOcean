from dataclasses import dataclass
from typing import TypeVar

from backtrader import Strategy

StrategyClass = TypeVar("StrategyClass", bound=Strategy)


@dataclass
class StrategyPageData:
    cls: StrategyClass
    notes: list[tuple[str, str]]
    source: str
    params: list[tuple[str, any]]


strategy_registry: list[StrategyPageData] = []
