import datetime
from dataclasses import dataclass, field
from typing import Any

from blueOcean.application.dto import ContextInfo, SessionInfo
from blueOcean.domain.ohlcv import Timeframe


@dataclass(frozen=True)
class OhlcvFetchDialogState:
    exchange: str = field(default="")
    symbol: str = field(default="")
    exchanges: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BacktestDialogState:
    source: str = field(default="")
    symbol: str = field(default="")
    timeframe: Timeframe = field(default=Timeframe.ONE_MINUTE)
    strategy: str | None = field(default=None)
    strategy_args: dict[str, Any] = field(default_factory=dict)
    start_date: datetime.date | None = field(default=None)
    end_date: datetime.date | None = field(default=None)


@dataclass(frozen=True)
class SessionTopPageState:
    sessions: list[SessionInfo] = field(default_factory=list)


@dataclass(frozen=True)
class SessionDetailPageState:
    session: SessionInfo | None = field(default=None)
    contexts: list[ContextInfo] = field(default_factory=list)
