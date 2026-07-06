from cryptography.fernet import Fernet
from injector import Binder, Injector, Module, provider, singleton
from peewee import SqliteDatabase

from blueOcean.database.repositories import MT5AccountRepository
from blueOcean.models import IAccountRepository
from blueOcean.settings import Settings, get_settings


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


injector = Injector(
    [
        SettingsModule(get_settings()),
        DatabaseModule(),
        SecurityModule(),
    ]
)


def get_injector() -> Injector:
    return injector
