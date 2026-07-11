from cryptography.fernet import Fernet
from injector import Binder, Injector, Module, provider, singleton
from peewee import SqliteDatabase

from blueOcean.database.repositories import MT5AccountRepository
from blueOcean.models import IAccountRepository
from blueOcean.metatrader.workers import MT5WorkerManager
from blueOcean.settings import Settings, get_settings
from blueOcean.strategy.repositories import StrategyRepository, StrategyRunRepository
from blueOcean.strategy.supervisor import StrategySupervisor


class SettingsModule(Module):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configure(self, binder: Binder) -> None:
        binder.bind(Settings, to=self.settings, scope=singleton)


class DatabaseModule(Module):
    @provider
    @singleton
    def database(self, settings: Settings) -> SqliteDatabase:
        return SqliteDatabase(
            settings.sqlite_path,
            pragmas={"foreign_keys": 1, "journal_mode": "wal"},
        )
    
    @provider
    def account_repository(self, database: SqliteDatabase) -> IAccountRepository:
        return MT5AccountRepository(database)


class SecurityModule(Module):
    @provider
    @singleton
    def password_cipher(self, settings: Settings) -> Fernet:
        return Fernet(settings.mt5_secret_key.get_secret_value().encode())


class MT5Module(Module):
    @provider
    @singleton
    def mt5_worker_manager(self, settings: Settings) -> MT5WorkerManager:
        return MT5WorkerManager(startup_timeout=settings.mt5_startup_timeout_seconds)


class StrategyModule(Module):
    @provider
    @singleton
    def strategy_repository(self) -> StrategyRepository:
        return StrategyRepository()

    @provider
    @singleton
    def strategy_run_repository(self) -> StrategyRunRepository:
        return StrategyRunRepository()

    @provider
    @singleton
    def strategy_supervisor(
        self,
        strategies: StrategyRepository,
        runs: StrategyRunRepository,
    ) -> StrategySupervisor:
        return StrategySupervisor(strategies, runs)


injector = Injector(
    [
        SettingsModule(get_settings()),
        DatabaseModule(),
        SecurityModule(),
        MT5Module(),
        StrategyModule(),
    ]
)


def get_injector() -> Injector:
    return injector
