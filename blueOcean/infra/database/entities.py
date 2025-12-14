from __future__ import annotations

from datetime import datetime

import cuid2
from peewee import (
    BooleanField,
    CharField,
    DatabaseProxy,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SmallIntegerField,
    TextField,
)

from blueOcean.domain.account import Account, ApiCredential

proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = proxy


class AccountEntity(BaseModel):
    id = CharField(primary_key=True, default=lambda: cuid2.Cuid().generate())
    api_key = CharField()
    api_secret = CharField()
    exchange_name = CharField(index=True)
    is_sandbox = BooleanField(default=False)
    label = CharField(unique=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "accounts"
        indexes = ((("exchange_name", "is_sandbox", "api_key"), True),)

    def to_domain(self) -> Account:
        return Account(
            credential=ApiCredential(
                exchange=self.exchange_name,
                key=self.api_key,
                secret=self.api_secret,
                is_sandbox=self.is_sandbox,
            ),
            label=self.label,
        )

    @classmethod
    def from_domain(cls, account: Account) -> AccountEntity:
        return cls.create(
            api_key=account.credential.key,
            api_secret=account.credential.secret,
            exchange_name=account.credential.exchange,
            is_sandbox=account.credential.is_sandbox,
            label=account.label,
        )


class BotEntity(BaseModel):
    id = CharField(primary_key=True, default=lambda: cuid2.Cuid().generate())
    pid = IntegerField()
    status = SmallIntegerField()
    account = ForeignKeyField(AccountEntity, backref="bots")
    strategy_name = CharField()
    strategy_args = TextField()
    label = CharField()
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "bots"
