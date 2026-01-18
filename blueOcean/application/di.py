from injector import InstanceProvider, Module, provider, singleton
from peewee import SqliteDatabase

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.application.services import (
    BacktestExchangeService,
    CcxtExchangeService,
    IExchangeService,
)
from blueOcean.domain.context import IContextRepository
from blueOcean.domain.ohlcv import IOhlcvRepository
from blueOcean.domain.session import ISessionRepository
from blueOcean.domain.strategy import IStrategySnapshotRepository
from blueOcean.infra.accessors import ExchangeSymbolDirectoryAccessor
from blueOcean.infra.database.entities import entities, proxy
from blueOcean.infra.database.repositories import (
    ContextRepository,
    OhlcvRepository,
    SessionRepository,
    StrategySnapshotRepository,
)
from blueOcean.infra.factories import OhlcvFetcherFactory


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
        db.create_tables(entities)
        return db


class AppModule(Module):
    def configure(self, binder):
        binder.install(AppDatabaseModule())

        binder.bind(ISessionRepository, to=SessionRepository)
        binder.bind(IContextRepository, to=ContextRepository)
        binder.bind(IStrategySnapshotRepository, to=StrategySnapshotRepository)
        binder.bind(IOhlcvRepository, to=OhlcvRepository)
        binder.bind(IOhlcvFetcherFactory, to=OhlcvFetcherFactory)


class FetchModule(Module):
    def configure(self, binder):
        binder.bind(IExchangeService, to=CcxtExchangeService)


class SessionDetailModule(Module):
    def __init__(self, id: str):
        self._id = id

    def configure(self, binder):
        binder.bind(str, to=InstanceProvider(self._id))


class BacktestDialogModule(Module):
    def __init__(self):
        super().__init__()

    def configure(self, binder):
        binder.bind(IExchangeSymbolAccessor, to=ExchangeSymbolDirectoryAccessor)
        binder.bind(IExchangeService, to=BacktestExchangeService)
