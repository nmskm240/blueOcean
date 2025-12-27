import datetime
from dataclasses import dataclass, field
from typing import Any

from blueOcean.application.dto import AccountCredentialInfo
from blueOcean.domain.ohlcv import Timeframe


@dataclass(frozen=True)
class OhlcvFetchDialogState:
    accout: AccountCredentialInfo = field(default=None)
    symbol: str = field(default="")
    accounts: list[AccountCredentialInfo] = field(default_factory=list)


@dataclass(frozen=True)
class OhlcvCsvUploadDialogState:
    exchange: str = field(default="")
    symbol: str = field(default="")
    file_path: str = field(default="")


@dataclass(frozen=True)
class BacktestDialogState:
    source: str = field(default="")
    symbol: str = field(default="")
    timeframe: Timeframe = field(default=Timeframe.ONE_MINUTE)
    strategy: str | None = field(default=None)
    strategy_args: dict[str, Any] = field(default_factory=dict)
    start_date: datetime.date | None = field(default=None)
    end_date: datetime.date | None = field(default=None)
