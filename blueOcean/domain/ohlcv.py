from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import IntEnum
from typing import Generator

import backtrader as bt
import pandas as pd


@dataclass
class Ohlcv:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def to_dataframe(cls, ohlcvs: list[Ohlcv]) -> pd.DataFrame:
        df = pd.DataFrame([asdict(c) for c in ohlcvs])
        if not df.empty:
            df = df.set_index("time")
        return df

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> list[Ohlcv]:
        return [cls(**row) for row in df.reset_index(drop=True).to_dict("records")]


class Timeframe(IntEnum):
    ONE_MINUTE = 1
    FIVE_MINUTE = 5
    FIFTEEN_MINUTE = 15
    THIRTY_MINUTE = 30
    ONE_HOUR = 60
    FOUR_HOUR = 240
    ONE_DAY = 1440

    def to_duck(self) -> str:
        return f"'{int(self)} minutes'"

    def to_backtrade(self) -> bt.TimeFrame:
        match self:
            case Timeframe.ONE_DAY:
                return bt.TimeFrame.Days
            case _:
                return bt.TimeFrame.Minutes


class IOhlcvRepository(metaclass=ABCMeta):
    @abstractmethod
    def save(self, ohlcv: list[Ohlcv], source: str, symbol: str):
        raise NotImplementedError()

    @abstractmethod
    def get_latest_timestamp(self, source: str, symbol: str) -> datetime | None:
        raise NotImplementedError()

    @abstractmethod
    def find(
        self,
        symbol: str,
        source: str,
        interval: Timeframe = Timeframe.ONE_MINUTE,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Ohlcv]:
        raise NotImplementedError()


class OhlcvFetcher(metaclass=ABCMeta):
    @property
    @abstractmethod
    def source(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def longest_since(self) -> datetime:
        raise NotImplementedError()

    def fetch_ohlcv(self, symbol: str, since_at: datetime | None = None):
        _since_at = since_at or self.longest_since
        yield from self._fetch_ohlcv_process(symbol, _since_at)

    @abstractmethod
    def _fetch_ohlcv_process(
        self, symbol: str, since_at: datetime
    ) -> Generator[list[Ohlcv]]:
        raise NotImplementedError()
