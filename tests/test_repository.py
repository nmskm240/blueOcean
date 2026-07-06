import pytest
from peewee import SqliteDatabase

from blueOcean.database.schemas import AccountSchema, proxy
from blueOcean.database.repositories import MT5AccountRepository
from blueOcean.models import Account, AccountId, AccountNotFoundError, Mt5Connection


@pytest.fixture
def repository(tmp_path):
    database = SqliteDatabase(tmp_path / "accounts.db")
    proxy.initialize(database)
    with database.connection_context():
        database.create_tables([AccountSchema])
        yield MT5AccountRepository(database)


def test_get_by_id_returns_account(repository):
    account_id = repository.save(
        Account(
            id=None,
            name="Demo",
            connection=Mt5Connection(
                r"C:\MT5\terminal64.exe", "Broker-Demo", 12345678, b"encrypted-secret"
            ),
            portable=False,
        )
    )

    account = repository.get_by_id(account_id)

    assert isinstance(account_id, AccountId)
    assert account.id == account_id
    assert account.name == "Demo"


def test_get_by_id_raises_when_account_does_not_exist(repository):
    with pytest.raises(AccountNotFoundError):
        repository.get_by_id(AccountId("missing-account"))
