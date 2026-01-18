from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DatetimeRange:
    start_at: datetime = field(default=datetime.min)
    end_at: datetime = field(default=datetime.max)

    def between(self, date: datetime):
        return self.start_at <= date < self.end_at


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    name: str


@dataclass(frozen=True)
class ContextInfo:
    context_id: str
    session_id: str
    strategy_snapshot_id: str
    source: str
    symbol: str
    timeframe: str
    start_at: datetime
    end_at: datetime
    strategy_args: dict[str, object]


@dataclass(frozen=True)
class TimeReturnPoint:
    timestamp: datetime
    analyzer: str
    key: str
    value: float
