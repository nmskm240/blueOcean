from __future__ import annotations

import time
from abc import ABCMeta, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from queue import Empty
from typing import Generator

import backtrader as bt
import ccxt
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from blueOcean.logging import logger


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


class OhlcvRepository(IOhlcvRepository):
    def __init__(self, base_path: str = "./data"):
        self._base_dir = base_path
        self.__con = duckdb.connect()

    def _parse_from_symbol_to_dir(self, symbol: str) -> str:
        return symbol.replace("/", "_")

    def save(self, ohlcv, source, symbol):
        df = Ohlcv.to_dataframe(ohlcv)
        df = df.sort_index()

        df["year_month"] = df.index.strftime("%Y-%m")

        for ym, chunk in df.groupby("year_month"):
            symbol_dir = self._parse_from_symbol_to_dir(symbol)
            out_dir = Path(self._base_dir, source, symbol_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = Path(out_dir, f"{ym}.parquet")
            chunk = chunk.drop(columns=["year_month"])
            chunk["time"] = chunk.index
            chunk = chunk[["time", "open", "high", "low", "close", "volume"]]
            table = pa.Table.from_pandas(chunk, preserve_index=False)

            if filename.exists():
                old = pq.read_table(filename).to_pandas()
                merged = (
                    pd.concat([old, chunk], ignore_index=True)
                    .drop_duplicates(subset=["time"])
                    .sort_values("time")
                )
                table = pa.Table.from_pandas(merged, preserve_index=False)

            logger.info(f"{symbol} {ym} parquet update")
            pq.write_table(table, filename)

    def get_latest_timestamp(self, source, symbol):
        symbol_dir = self._parse_from_symbol_to_dir(symbol)
        path = Path(self._base_dir, source, symbol_dir, "*.parquet")

        sql = f"""
            SELECT max(time) AS latest
            FROM read_parquet('{path}')
        """

        try:
            row = self.__con.execute(sql).fetchone()
            return pd.to_datetime(row[0]).to_pydatetime()
        except:
            return None

    def find(
        self,
        symbol,
        source,
        timeframe=Timeframe.ONE_MINUTE,
        start_date=None,
        end_date=None,
    ):
        symbol_dir = self._parse_from_symbol_to_dir(symbol)
        path = Path(self._base_dir, source, symbol_dir, "*.parquet")

        where = []
        if start_date:
            where.append(f"time >= '{start_date.isoformat()}'")
        if end_date:
            where.append(f"time <= '{end_date.isoformat()}'")

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        sql = f"""
                SELECT
                    time_bucket(INTERVAL {timeframe.to_duck()}, time) AS time,
                    first(open) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    last(close) AS close,
                    sum(volume) AS volume
                FROM read_parquet('{path}')
                {where_sql}
                GROUP BY 1
                ORDER BY time
            """
        df = self.__con.execute(sql).df()
        return Ohlcv.from_dataframe(df)


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


class CcxtOhlcvFetcher(OhlcvFetcher):
    TIMEFRAME = "1m"

    def __init__(self, exchange: ccxt.Exchange):
        super().__init__()
        self.exchange = exchange
        self.exchange.load_markets()

    @property
    def source(self) -> str:
        return self.exchange.name

    @property
    def longest_since(self):
        return datetime(2017, 1, 1, tzinfo=UTC)

    def _fetch_ohlcv_process(self, symbol: str, since_at: datetime):
        timeframe_ms = self.exchange.parse_timeframe(self.TIMEFRAME) * 1000
        since = int(since_at.timestamp() * 1000) + timeframe_ms

        while since < self.exchange.milliseconds():
            fetched = self._try_fetch(symbol, since)
            if not fetched:
                break

            df = pd.DataFrame(
                fetched,
                columns=["time", "open", "high", "low", "close", "volume"],
            )
            df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)

            if not df.empty:
                logger.info(
                    f'Fetched from {self.exchange.name} {symbol} {df["time"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")}~{df["time"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")}'
                )

            ohlcvs = Ohlcv.from_dataframe(df)

            if ohlcvs:
                yield ohlcvs

            last_time = ohlcvs[-1].time
            since = int(last_time.timestamp() * 1000) + timeframe_ms

            time.sleep(self.exchange.rateLimit / 1000)

    def _try_fetch(self, symbol: str, since: int):
        """3回リトライ"""
        for attempt in range(3):
            try:
                return self.exchange.fetch_ohlcv(
                    symbol, self.TIMEFRAME, since=since, limit=1000
                )
            except Exception as e:
                if attempt == 2:
                    raise
                logger.warning(f"Retry fetch due to error: {e}")
                time.sleep(1)


class LocalDataFeed(bt.feed.DataBase):
    lines = ("datetime", "open", "high", "low", "close", "volume", "openinterest")

    params = (
        ("repository", None),
        ("symbol", None),
        ("source", None),
        ("ohlcv_timeframe", Timeframe.ONE_MINUTE),
        ("start_at", datetime.min),
        ("end_at", datetime.max),
        # Feed内部のtimeframe用
        ("timeframe", bt.TimeFrame.NoTimeFrame),
    )

    def __init__(self):
        super().__init__()
        self._data_iter = None
        # NOTE: timeframeとcompressionをAnalyzerなどが利用するため明示が必要
        self.p.timeframe = self.p.ohlcv_timeframe.to_backtrade()
        self.p.compression = 1

    def start(self):
        super().start()

        ohlcvs = self.p.repository.find(
            symbol=self.p.symbol,
            source=self.p.source,
            timeframe=self.p.ohlcv_timeframe,
            start_date=self.p.start_at,
            end_date=self.p.end_at,
        )

        self._data_iter = iter(
            [(o.time, o.open, o.high, o.low, o.close, o.volume) for o in ohlcvs]
        )

    def _load(self):
        if self._data_iter is None:
            return False

        try:
            dt_, o, h, l, c, v = next(self._data_iter)
        except StopIteration:
            return False

        if hasattr(dt_, "to_pydatetime"):
            dt_ = dt_.to_pydatetime()
        if dt_.tzinfo is not None:
            dt_ = dt_.replace(tzinfo=None)

        self.lines.datetime[0] = bt.date2num(dt_)
        self.lines.open[0] = o
        self.lines.high[0] = h
        self.lines.low[0] = l
        self.lines.close[0] = c
        self.lines.volume[0] = v
        self.lines.openinterest[0] = 0.0

        return True


class QueueDataFeed(bt.feed.DataBase):
    lines = (
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "openinterest",
    )

    params = (
        ("queue", None),
        ("symbol", None),
    )

    def islive(self):
        return True

    def _load(self):
        try:
            tick = self.p.queue.get(timeout=1)
        except Empty:
            return None

        self.lines.datetime[0] = bt.date2num(tick.time)
        self.lines.close[0] = tick.close
        self.lines.open[0] = tick.open
        self.lines.high[0] = tick.high
        self.lines.low[0] = tick.low
        self.lines.volume[0] = tick.volume
        self.lines.openinterest[0] = 0.0

        return True
