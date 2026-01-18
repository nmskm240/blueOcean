from __future__ import annotations

from abc import ABCMeta, abstractmethod

import ccxt
from injector import inject

from blueOcean.application.accessors import IExchangeSymbolAccessor


class IExchangeService(metaclass=ABCMeta):
    @abstractmethod
    def fetchable_exchanges(self) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def symbols_for(self, exchange_name: str) -> list[str]:
        raise NotImplementedError()


class CcxtExchangeService(IExchangeService):
    def fetchable_exchanges(self) -> list[str]:
        return list(ccxt.exchanges)

    def symbols_for(self, exchange_name: str) -> list[str]:
        exchange_cls = getattr(ccxt, exchange_name, None)
        if exchange_cls is None:
            return []
        exchange = exchange_cls()
        markets = exchange.load_markets()
        return sorted(markets.keys())


class BacktestExchangeService(IExchangeService):
    @inject
    def __init__(self, accessor: IExchangeSymbolAccessor):
        self._accessor = accessor

    def fetchable_exchanges(self) -> list[str]:
        return sorted(self._accessor.exchanges)

    def symbols_for(self, exchange_name: str) -> list[str]:
        return sorted(self._accessor.symbols_for(exchange_name))
