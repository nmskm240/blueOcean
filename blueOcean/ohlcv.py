from __future__ import annotations
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
import logging
from pathlib import Path
import time
from typing import Generator
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import asdict
import ccxt


logger = logging.getLogger(__name__)


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
    ONE_HOUR = 60
    FOUR_HOUR = 240
    ONE_DAY = 1440

    def to_duck(self) -> str:
        return f"'{int(self)} minutes'"


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
        end_date: datetime | None = None
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
            table = pa.Table.from_pandas(chunk,preserve_index=False)

            if filename.exists():
                old = pq.read_table(filename).to_pandas()
                merged = ( 
                    pd.concat([old, chunk], ignore_index=True) 
                    .drop_duplicates(subset=["time"]) 
                    .sort_values("time") )
                table = pa.Table.from_pandas(merged, preserve_index=False)

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
        
    def find(self, symbol, source, timeframe = Timeframe.ONE_MINUTE, start_date = None, end_date = None):
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
    def __init__(self, source: str):
        self._source = source

    @property
    @abstractmethod
    def longest_since(self) -> datetime:
        raise NotImplementedError()

    def fetch_ohlcv(self, symbol: str, since_at: datetime | None = None):
        _since_at = since_at or self.longest_since
        yield from self._fetch_ohlcv_process(symbol, _since_at)

    @abstractmethod
    def _fetch_ohlcv_process(self, symbol: str, since_at: datetime) -> Generator[list[Ohlcv]]:
        raise NotImplementedError()


class CcxtOhlcvFetcher(OhlcvFetcher):
    TIMEFRAME = "1m"

    @property
    def longest_since(self):
        return datetime(2017, 1, 1, tzinfo=UTC)

    def _fetch_ohlcv_process(self, symbol: str, since_at: datetime):
        meta: type[ccxt.Exchange] = getattr(ccxt, self._source)
        exchange = meta()
        exchange.load_markets()

        timeframe_ms = exchange.parse_timeframe(self.TIMEFRAME) * 1000
        since = int(since_at.timestamp() * 1000) + timeframe_ms

        while since < exchange.milliseconds():
            fetched = self._try_fetch(exchange, symbol, since)
            if not fetched:
                break

            df = pd.DataFrame(
                fetched,
                columns=["time", "open", "high", "low", "close", "volume"],
            )
            df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)

            if not df.empty:
                logger.info(
                    f'Fetched {df["time"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")}~{df["time"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")}'
                )

            ohlcvs = Ohlcv.from_dataframe(df)

            if ohlcvs:
                yield ohlcvs

            last_time = ohlcvs[-1].time
            since = int(last_time.timestamp() * 1000) + timeframe_ms

            time.sleep(exchange.rateLimit / 1000)

    def _try_fetch(self, exchange: ccxt.Exchange, symbol: str, since: int):
        """3回リトライ"""
        for attempt in range(3):
            try:
                return exchange.fetch_ohlcv(
                    symbol, self.TIMEFRAME, since=since, limit=1000
                )
            except Exception as e:
                if attempt == 2:
                    raise
                logger.warning(f"Retry fetch due to error: {e}")
                time.sleep(1)
