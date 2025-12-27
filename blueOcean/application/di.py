from abc import ABCMeta, abstractmethod
from pathlib import Path
from queue import Queue

import backtrader as bt
import duckdb
from injector import Module, provider, singleton
from peewee import SqliteDatabase

from blueOcean.application.accessors import (
    IBotRuntimeDirectoryAccessor,
    IExchangeSymbolAccessor,
)
from blueOcean.application.analyzers import StreamingAnalyzer
from blueOcean.application.broker import Broker
from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.application.feed import LocalDataFeed, QueueDataFeed
from blueOcean.application.services import (
    BacktestExchangeService,
    BotWorkerFactory,
    CcxtExchangeService,
    IExchangeService,
)
from blueOcean.application.store import IStore
from blueOcean.domain.bot import (
    BacktestContext,
    BotContext,
    BotId,
    IBotRepository,
    IBotWorkerFactory,
    LiveContext,
)
from blueOcean.domain.ohlcv import IOhlcvRepository
from blueOcean.infra.accessors import (
    ExchangeSymbolDirectoryAccessor,
    LocalBotRuntimeDirectoryAccessor,
)
from blueOcean.infra.database.entities import (
    AccountEntity,
    BotContextEntity,
    BotEntity,
    proxy,
)
from blueOcean.infra.database.repositories import BotRepository, OhlcvRepository
from blueOcean.infra.factories import OhlcvFetcherFactory
from blueOcean.infra.stores import CcxtSpotStore


class HistoricalDataModule(Module):
    @singleton
    @provider
    def connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect("./data")


class AppDatabaseModule(Module):
    @singleton
    @provider
    def connection(self) -> SqliteDatabase:
        db = SqliteDatabase(
            "./data/blueOcean.sqlite3",
            pragmas={
                "foreign_keys": True,
            },
        )
        proxy.initialize(db)
        db.create_tables(
            [
                AccountEntity,
                BotEntity,
                BotContextEntity,
            ]
        )
        return db


class AppModule(Module):
    def configure(self, binder):
        binder.install(AppDatabaseModule())
        binder.install(HistoricalDataModule())

        binder.bind(IBotRepository, to=BotRepository)
        binder.bind(IBotWorkerFactory, to=BotWorkerFactory)
        binder.bind(IOhlcvRepository, to=OhlcvRepository)
        binder.bind(IOhlcvFetcherFactory, to=OhlcvFetcherFactory)


class FetchModule(Module):
    def configure(self, binder):
        binder.bind(IExchangeService, to=CcxtExchangeService)


class IBotRunTimeModule(Module, metaclass=ABCMeta):
    def __init__(self, id: BotId, context: BotContext):
        self._id = id
        self._context = context

    def configure(self, binder):
        binder.install(AppDatabaseModule())

        binder.bind(IOhlcvFetcherFactory, to=OhlcvFetcherFactory)
        binder.bind(
            IBotRuntimeDirectoryAccessor,
            to=LocalBotRuntimeDirectoryAccessor,
        )

    @provider
    @singleton
    def directory(self, accessor: IBotRuntimeDirectoryAccessor) -> Path:
        return accessor.generate_directory(self._id)

    @provider
    @abstractmethod
    def cerebro_engine(self) -> bt.Cerebro:
        raise NotImplementedError()


class LiveTradeRuntimeModule(IBotRunTimeModule):
    def __init__(self, id: BotId, context: LiveContext):
        super().__init__(id, context)

    def configure(self, binder):
        super().configure(binder)

        binder.bind(IStore, to=CcxtSpotStore)
        binder.bind(Queue, to=Queue, scope=singleton)
        binder.bind(bt.feed.DataBase, to=QueueDataFeed)
        binder.bind(bt.broker.BrokerBase, to=Broker)

    @provider
    def cerebro_engine(
        self,
        broker: bt.broker.BrokerBase,
        feed: bt.feed.DataBase,
        run_directory: Path,
    ) -> bt.Cerebro:
        cerebro = bt.Cerebro()
        cerebro.broker = broker
        cerebro.adddata(feed)
        cerebro.addanalyzer(bt.analyzers.TimeReturn)
        cerebro.addanalyzer(
            StreamingAnalyzer,
            analyzers=["timereturn"],
            path=run_directory,
        )
        cerebro.addstrategy(self.context.strategy_cls, **self.context.strategy_args)
        return cerebro


class BacktestRuntimeModule(IBotRunTimeModule):
    def __init__(self, id: BotId, context: BacktestContext):
        super().__init__(id, context)

    def configure(self, binder):
        super().configure(binder)
        binder.install(HistoricalDataModule())

        binder.bind(IOhlcvRepository, OhlcvRepository)
        binder.bind(IExchangeSymbolAccessor, to=ExchangeSymbolDirectoryAccessor)
        binder.bind(IExchangeService, to=BacktestExchangeService)

    @provider
    def feed(self, repository: IOhlcvRepository) -> bt.feed.DataBase:
        return LocalDataFeed(
            repository=repository,
            symbol=self.context.symbol,
            source=self.context.source,
            ohlcv_timeframe=self.context.timeframe,
            start_at=self.context.start_at,
            end_at=self.context.end_at,
        )

    @provider
    def cerebro_engine(
        self,
        feed: bt.feed.DataBase,
        run_directory: Path,
    ) -> bt.Cerebro:
        cerebro = bt.Cerebro()
        cerebro.adddata(feed)
        cash = getattr(self.context, "cash", None)
        if cash is not None:
            cerebro.broker.setcash(cash)
        cerebro.addanalyzer(bt.analyzers.TimeReturn)
        cerebro.addanalyzer(
            StreamingAnalyzer,
            analyzers=["timereturn"],
            path=run_directory,
        )
        cerebro.addstrategy(self.context.strategy_cls, **self.context.strategy_args)
        return cerebro


class BacktestDialogModule(Module):
    def __init__(self):
        super().__init__()

    def configure(self, binder):
        binder.bind(IExchangeSymbolAccessor, to=ExchangeSymbolDirectoryAccessor)
        binder.bind(IExchangeService, to=BacktestExchangeService)
