from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from cuid2 import Cuid
from blueOcean.strategy.registry import get_strategy_definition


def new_id() -> str:
    return Cuid().generate()


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    definition_key: str
    account_id: str | None
    symbol: str
    timeframe: str
    data_source: str = "synthetic"
    execution_backend: str = "paper"
    history_period: str = "1y"
    initial_cash: float = 100_000.0
    commission: float = 0.001
    parameters: dict = field(default_factory=dict)
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("戦略名は必須です")
        validated_parameters = get_strategy_definition(self.definition_key).validate(self.parameters)
        object.__setattr__(self, "parameters", validated_parameters)
        if not self.symbol.strip():
            raise ValueError("シンボルは必須です")
        if not self.timeframe.strip():
            raise ValueError("時間足は必須です")
        if (self.data_source, self.execution_backend) not in {
            ("synthetic", "paper"),
            ("yfinance", "backtest"),
        }:
            raise ValueError("価格データと実行方法の組み合わせが正しくありません")
        if self.initial_cash <= 0:
            raise ValueError("初期資金は正数で指定してください")
        if self.commission < 0:
            raise ValueError("commissionは0以上で指定してください")


@dataclass(frozen=True)
class StrategyRun:
    strategy_id: str
    state: str = "starting"
    id: str = field(default_factory=new_id)
    pid: int | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    heartbeat_at: datetime | None = None
    stopped_at: datetime | None = None
    result: dict | None = None


class StrategyNotFoundError(LookupError):
    pass


class StrategyRunNotFoundError(LookupError):
    pass


class StrategyAlreadyRunningError(RuntimeError):
    pass
