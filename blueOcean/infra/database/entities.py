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
