from __future__ import annotations

from injector import inject
from peewee import DoesNotExist, SqliteDatabase

from blueOcean.database.schemas import AccountSchema
from blueOcean.models import Account, AccountId, AccountNotFoundError, IAccountRepository


class MT5AccountRepository(IAccountRepository):
    """Persist domain ``Account`` objects without interpreting credentials."""

    @inject
    def __init__(self, database: SqliteDatabase) -> None:
        if database.is_closed():
            raise RuntimeError("MT5AccountRepository requires an open database connection")
        self.database = database

    def list(self) -> list[Account]:
        return [record.to_entity() for record in AccountSchema.select().order_by(AccountSchema.name)]

    def get_by_id(self, id: AccountId) -> Account:
        try:
            return AccountSchema.get_by_id(id.value).to_entity()
        except DoesNotExist as exc:
            raise AccountNotFoundError("Account not found") from exc

    def save(self, account: Account) -> AccountId:
        values = {
            "name": account.name,
            "path": account.connection.path,
            "login": account.connection.login,
            "server": account.connection.server,
            "portable": account.portable,
            "password_encrypted": account.connection.encrypted_password,
        }
        record = AccountSchema.get_or_none(AccountSchema.id == account.id.value)
        if record:
            AccountSchema.update(**values).where(AccountSchema.id == account.id.value).execute()
        else:
            AccountSchema.create(id=account.id.value, **values)
        return account.id

    def delete_by_id(self, id: AccountId) -> None:
        AccountSchema.delete_by_id(id.value)
