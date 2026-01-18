import ccxt

from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.domain.ohlcv import OhlcvFetcher
from blueOcean.infra.fetchers import CcxtOhlcvFetcher


class OhlcvFetcherFactory(IOhlcvFetcherFactory):
    def create(self, exchange_name: str) -> OhlcvFetcher:
        exchange_cls = getattr(ccxt, exchange_name, None)
        if exchange_cls is None:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        exchange = exchange_cls()
        return CcxtOhlcvFetcher(exchange)
