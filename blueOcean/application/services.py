from __future__ import annotations

from abc import ABCMeta, abstractmethod

import ccxt
from injector import inject

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.domain.bot import (
    Bot,
    BotContext,
    BotId,
    BotRunMode,
    IBotRepository,
    IBotWorkerFactory,
)


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
