from __future__ import annotations

from abc import ABCMeta, abstractmethod

import ccxt
from injector import inject

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.domain.bot import (Bot, BotContext, BotId, BotRunMode,
                                  IBotRepository, IBotWorkerFactory)
from blueOcean.domain.ohlcv import IOhlcvRepository
from blueOcean.infra.database.repositories import AccountRepository


class IExchangeService(metaclass=ABCMeta):
    @abstractmethod
    def fetchable_exchanges(self) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def symbols_for(self, exchange_name: str) -> list[str]:
        raise NotImplementedError()


class BotWorkerFactory(IBotWorkerFactory):
    def create(self, id: BotId, context: BotContext):
        if context.mode is not BotRunMode.BACKTEST:
            raise RuntimeError(f"Unsupported run mode. {context.mode}")
        from blueOcean.application.workers import BacktestWorker

        worker = BacktestWorker(id, context)
        return worker


class BotExecutionService:
    @inject
    def __init__(
        self,
        bot_repository: IBotRepository,
        bot_worker_factory: IBotWorkerFactory,
    ):
        self._bot_repository = bot_repository
        self._bot_worker_factory = bot_worker_factory

    def start(self, context: BotContext):
        bot = Bot.create(context)
        worker = self._bot_worker_factory.create(bot.id, context)

        bot.attach(worker)
        bot.start()
        saved = self._bot_repository.save(bot)
        return saved.id

    def stop(self, id: BotId):
        from blueOcean.application.workers import RecoverWorker

        bot = self._bot_repository.find_by_id(id)
        worker = RecoverWorker(bot.pid)

        bot.attach(worker)
        bot.stop()
        self._bot_repository.save(bot)


class CcxtExchangeService(IExchangeService):
    @inject
    def __init__(
        self,
        account_repository: AccountRepository,
        ohlcv_repository: IOhlcvRepository,
    ):
        self._account_repository = account_repository
        self._ohlcv_repository = ohlcv_repository

    def fetchable_exchanges(self) -> list[str]:
        supported: list[str] = []
        for account in self._account_repository.get_all():
            credential = account.credential
            if not credential.key or not credential.secret:
                continue
            name = credential.exchange
            if name in supported:
                continue
            exchange_cls = getattr(ccxt, name, None)
            if exchange_cls is None:
                continue
            exchange = exchange_cls(
                {
                    "apiKey": credential.key,
                    "secret": credential.secret,
                }
            )
            exchange.set_sandbox_mode(credential.is_sandbox)
            if exchange.has.get("fetchOHLCV"):
                supported.append(name)
        return supported

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
