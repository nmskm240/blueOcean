import datetime
from dataclasses import dataclass, field
from typing import Any

from blueOcean.application.dto import (
    AccountCredentialInfo,
    BotInfo,
    NotebookParameterInfo,
    PlaygroundRunInfo,
    TimeReturnPoint,
)
from blueOcean.domain.ohlcv import Timeframe


@dataclass(frozen=True)
class OhlcvFetchDialogState:
    account: AccountCredentialInfo = field(default=None)
    symbol: str = field(default="")
    accounts: list[AccountCredentialInfo] = field(default_factory=list)


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
class BotTopPageState:
    bots: list[BotInfo] = field(default_factory=list)


@dataclass(frozen=True)
class BotDetailPageState:
    info: BotInfo = field(default=None)
    time_returns: list[TimeReturnPoint] = field(default_factory=list)


@dataclass(frozen=True)
class PlaygroundPageState:
    notebooks: list[str] = field(default_factory=list)
    selected_notebook: str | None = field(default=None)
    parameters: list[NotebookParameterInfo] = field(default_factory=list)
    parameter_values: dict[str, str] = field(default_factory=dict)
    markdown: str = field(default="")
    is_loading: bool = field(default=False)
    error_message: str | None = field(default=None)


@dataclass(frozen=True)
class PlaygroundHistoryPageState:
    runs: list[PlaygroundRunInfo] = field(default_factory=list)


@dataclass(frozen=True)
class PlaygroundHistoryDetailPageState:
    run: PlaygroundRunInfo | None = field(default=None)
