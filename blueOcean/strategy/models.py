from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from cuid2 import Cuid


def new_id() -> str:
    return Cuid().generate()


@dataclass(frozen=True)
class Strategy:
    name: str
    account_id: str
    symbol: str
    timeframe: str
    mode: str = "paper"
    parameters: dict = field(default_factory=dict)
    id: str = field(default_factory=new_id)

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("戦略名は必須です")
        if not self.account_id.strip():
            raise ValueError("MT5アカウントは必須です")
        if not self.symbol.strip():
            raise ValueError("シンボルは必須です")
        if not self.timeframe.strip():
            raise ValueError("時間足は必須です")
        if self.mode not in {"paper", "demo", "live"}:
            raise ValueError("modeはpaper、demo、liveのいずれかです")


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


class StrategyNotFoundError(LookupError):
    pass


class StrategyRunNotFoundError(LookupError):
    pass


class StrategyAlreadyRunningError(RuntimeError):
    pass
