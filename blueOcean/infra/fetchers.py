import time
from datetime import UTC, datetime

import ccxt
import pandas as pd

from blueOcean.domain.ohlcv import Ohlcv, OhlcvFetcher
from blueOcean.infra.logging import logger


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
