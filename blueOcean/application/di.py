from queue import Queue
from typing import Type

import backtrader as bt
import ccxt
import duckdb
from injector import Module, provider, singleton
from peewee import SqliteDatabase

from blueOcean.application.analyzers import StreamingAnalyzer
from blueOcean.application.broker import Broker
from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.application.feed import LocalDataFeed, QueueDataFeed
from blueOcean.application.store import IStore
from blueOcean.domain.account import AccountId, ApiCredential
from blueOcean.domain.ohlcv import IOhlcvRepository, OhlcvFetcher, Timeframe
from blueOcean.infra.database.entities import AccountEntity, BotEntity, proxy
from blueOcean.infra.database.repositories import AccountRepository, OhlcvRepository
from blueOcean.infra.fetchers import CcxtOhlcvFetcher
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
        db = SqliteDatabase("./data/blueOcean.sqlite3", pragmas={"foreign_keys": True})
        proxy.initialize(db)
        db.create_tables(
            [
                AccountEntity,
                BotEntity,
            ]
        )
        return db


class ExchangeModule(Module):
    @singleton
    @provider
    def exchange(self, cred: ApiCredential) -> ccxt.Exchange:
        meta: Type[ccxt.Exchange] = getattr(ccxt, cred.exchange)
        ex = meta({"apiKey": cred.key, "secret": cred.secret})
        ex.set_sandbox_mode(cred.is_sandbox)
        ex.load_markets()
        return ex


class FetcherModule(Module):
    def configure(self, binder):
        binder.install(ExchangeModule())
        binder.install(HistoricalDataModule())

        binder.bind(IOhlcvRepository, to=OhlcvRepository)
        binder.bind(OhlcvFetcher, to=CcxtOhlcvFetcher)


class RealTradeModule(Module):
    def __init__(self, config: BotConfig):
        self.config = config

    def configure(self, binder):
        binder.install(ExchangeModule())
        binder.install(FetcherModule())
        binder.install(AppDatabaseModule())

        binder.bind(IStore, to=CcxtSpotStore)
        binder.bind(Queue, to=Queue, scope=singleton)
        binder.bind(bt.feed.DataBase, to=QueueDataFeed)
        binder.bind(bt.broker.BrokerBase, to=Broker)

    @singleton
    @provider
    def api_credential(self, repository: AccountRepository) -> ApiCredential:
        account = repository.get_by_id(AccountId(self.config.account_id))
        return account.credential

    @provider
    def cerebro_engine(
        self, broker: bt.broker.BrokerBase, feed: bt.feed.DataBase
    ) -> bt.Cerebro:
        cerebro = bt.Cerebro()
        cerebro.broker = broker
        cerebro.adddata(feed)
        cerebro.addanalyzer(bt.analyzers.TimeReturn)
        cerebro.addstrategy(self.config.strategy_cls, **self.config.strategy_args)
        return cerebro


class BacktestModule(Module):
    def __init__(self, config: BacktestConfig):
        self.config = config

    def configure(self, binder):
        binder.install(HistoricalDataModule())
        binder.install(AppDatabaseModule())

        binder.bind(IOhlcvRepository, OhlcvRepository)

    @provider
    def feed(self, repository: IOhlcvRepository) -> bt.feed.DataBase:
        return LocalDataFeed(
            repository=repository,
            symbol=self.config.symbol,
            source=self.config.source,
            ohlcv_timeframe=Timeframe.from_compression(self.config.compression),
            start_at=self.config.time_range.start_at,
            end_at=self.config.time_range.end_at,
        )

    @provider
    def cerebro_engine(self, feed: bt.feed.DataBase) -> bt.Cerebro:
        cerebro = bt.Cerebro()
        cerebro.adddata(feed)
        cerebro.broker.setcash(self.config.cash)
        cerebro.addanalyzer(bt.analyzers.TimeReturn)
        cerebro.addanalyzer(
            StreamingAnalyzer,
            analyzers=["timereturn"],
            path="./out/metrics.csv",
        )
        cerebro.addstrategy(self.config.strategy_cls, **self.config.strategy_args)
        return cerebro
