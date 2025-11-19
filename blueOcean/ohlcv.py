from __future__ import annotations
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import time
from typing import Generator
import pandas as pd
from dataclasses import asdict
import ccxt
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

BUCKET_NAME = "historical_data"
MEASUREMENT_NAME = "ohlcvs"

logger = logging.getLogger(__name__)


@dataclass
class Ohlcv:
    time: datetime
    symbol: str
    source: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    tick_volume: int | None = None
    spread: int | None = None

    def to_point(self) -> Point:
        point = (
            Point(MEASUREMENT_NAME)
            .tag("symbol", self.symbol)
            .tag("source", self.source)
            .field("open", self.open)
            .field("high", self.high)
            .field("low", self.low)
            .field("close", self.close)
            .field("volume", self.volume)
            .time(self.time)
        )

        if self.tick_volume is not None:
            point.field("tick_volume", self.tick_volume)
        if self.spread is not None:
            point.field("spread", self.spread)

        return point

    @classmethod
    def from_point(cls, point: Point):
        return cls(
            time=point.get_time(),
            symbol=point.get_tag("symbol"),
            source=point.get_tag("source"),
            open=point.get_field("open"),
            high=point.get_field("high"),
            low=point.get_field("low"),
            close=point.get_field("close"),
            volume=point.get_field("volume"),
            tick_volume=point.get_field("tick_volume"),
            spread=point.get_field("spread"),
        )

    @classmethod
    def to_dataframe(cls, ohlcvs: list[Ohlcv]) -> pd.DataFrame:
        df = pd.DataFrame([asdict(c) for c in ohlcvs])
        if not df.empty:
            df = df.set_index("time")
        return df

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> list[Ohlcv]:
        return [cls(**row) for row in df.reset_index(drop=True).to_dict("records")]

    @classmethod
    def from_flux_record(cls, record, symbol: str, source: str):
        values = record.values

        # Ensure essential fields are present
        required_fields = ["open", "high", "low", "close", "volume"]
        if not all(
            field in values and values[field] is not None for field in required_fields
        ):
            raise ValueError()

        return cls(
            time=values["_time"],
            symbol=symbol,
            source=source,
            open=values["open"],
            high=values["high"],
            low=values["low"],
            close=values["close"],
            volume=values["volume"],
            tick_volume=values.get("tick_volume"),
            spread=values.get("spread"),
        )


class IOhlcvRepository(metaclass=ABCMeta):
    @abstractmethod
    def save(self, ohlcv: list[Ohlcv]):
        raise NotImplementedError()

    @abstractmethod
    def get_latest_timestamp(self, exchange: str, symbol: str) -> datetime | None:
        raise NotImplementedError()

    @abstractmethod
    def find(
        self,
        symbol: str,
        source: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> list[Ohlcv]:
        raise NotImplementedError()


class OhlcvRepository(IOhlcvRepository):
    def __init__(self, client: InfluxDBClientAsync):
        self.client = client
        self.create_bucket_if_not_exists()

    async def save(self, ohlcvs: list[Ohlcv]):
        """OHLCVデータのリストをバッチで書き込みます。"""
        points = [o.to_point() for o in ohlcvs]
        write_api = self.client.write_api()
        await write_api.write(bucket=BUCKET_NAME, org=self.client.org, record=points)
        logger.info(f"Wrote {len(ohlcvs)} ohlcvs to InfluxDB.")

    async def create_bucket_if_not_exists(self):
        buckets_api = self.client.buckets_api()
        bucket = await buckets_api.find_bucket_by_name(BUCKET_NAME)
        if not bucket:
            logger.info(f"Create bucket {BUCKET_NAME}")
            await buckets_api.create_bucket(bucket_name=BUCKET_NAME)

    async def get_latest_timestamp(self, exchange: str, symbol: str) -> datetime | None:
        """InfluxDBから指定されたシンボルと時間足の最新のタイムスタンプを取得します。"""
        query = f"""
        from(bucket: "{BUCKET_NAME}")
          |> range(start: 0)
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT_NAME}")
          |> filter(fn: (r) => r.source == "{exchange}")
          |> filter(fn: (r) => r.symbol == "{symbol}")
          |> last()
        """
        api = self.client.query_api()
        tables = await api.query(query, org=self.client.org)
        if not tables or not tables[0].records:
            return None
        return tables[0].records[0].get_time()

    async def find(
        self,
        symbol: str,
        source: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str | None = None,
    ) -> list[Ohlcv]:
        """指定された条件でOhlcvデータ検索"""
        start_date = start_date or datetime(1970, 1, 1, tzinfo=UTC)
        end_date = end_date or datetime.now(UTC)

        ohlcvs: list[Ohlcv] = []
        api = self.client.query_api()
        start_dates = pd.date_range(start_date, end_date, freq="MS")

        for start in start_dates:
            end = (start + pd.offsets.MonthEnd()).to_pydatetime()
            query = self._build_query(symbol, source, start, end, timeframe)
            tables = await api.query(query, org=self.client.org)
            for table in tables:
                for record in table.records:
                    ohlcv = Ohlcv.from_flux_record(record, symbol, source)
                    if ohlcv:
                        ohlcvs.append(ohlcv)

        ohlcvs.sort(key=lambda x: x.time)

        return ohlcvs

    def _build_query(
        self,
        symbol: str,
        source: str,
        start: datetime,
        end: datetime,
        timeframe,
    ) -> str:
        base_query = f"""
        from(bucket: "{BUCKET_NAME}")
            |> range(start: {start.isoformat()}, stop: {end.isoformat()})
            |> filter(fn: (r) => r._measurement == "{MEASUREMENT_NAME}")
            |> filter(fn: (r) => r.symbol == "{symbol}")
            |> filter(fn: (r) => r.source == "{source}")
        """

        if not timeframe or timeframe == "1m":
            return f"""{base_query}
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """
        else:
            return f"""
            base = {base_query}

            o = base |> filter(fn: (r) => r._field == "open") |> aggregateWindow(every: {timeframe}, fn: first, createEmpty: false)
            h = base |> filter(fn: (r) => r._field == "high") |> aggregateWindow(every: {timeframe}, fn: max, createEmpty: false)
            l = base |> filter(fn: (r) => r._field == "low") |> aggregateWindow(every: {timeframe}, fn: min, createEmpty: false)
            c = base |> filter(fn: (r) => r._field == "close") |> aggregateWindow(every: {timeframe}, fn: last, createEmpty: false)
            v = base |> filter(fn: (r) => r._field == "volume") |> aggregateWindow(every: {timeframe}, fn: sum, createEmpty: false)
            tv = base |> filter(fn: (r) => r._field == "tick_volume") |> aggregateWindow(every: {timeframe}, fn: sum, createEmpty: false)

            union(tables: [o, h, l, c, v, tv])
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """


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
            df["symbol"] = symbol
            df["source"] = exchange.name

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
