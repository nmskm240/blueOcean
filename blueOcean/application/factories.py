from abc import ABCMeta, abstractmethod

from blueOcean.domain.account import AccountId
from blueOcean.domain.ohlcv import OhlcvFetcher


class IOhlcvFetcherFactory(metaclass=ABCMeta):
    @abstractmethod
    def create(self, account_id: AccountId) -> OhlcvFetcher:
        raise NotImplementedError()
