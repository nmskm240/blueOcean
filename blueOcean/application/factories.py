from abc import ABCMeta, abstractmethod

from blueOcean.domain.ohlcv import OhlcvFetcher


class IOhlcvFetcherFactory(metaclass=ABCMeta):
    @abstractmethod
    def create(self, exchange_name: str) -> OhlcvFetcher:
        raise NotImplementedError()
