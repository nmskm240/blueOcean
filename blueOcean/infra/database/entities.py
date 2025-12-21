from __future__ import annotations

from datetime import datetime

from peewee import (
    BooleanField,
    CharField,
    DatabaseProxy,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)

proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = proxy


class AccountEntity(BaseModel):
    id = CharField(primary_key=True)
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
    id = CharField(primary_key=True)
    status = IntegerField(index=True)
    pid = IntegerField(null=True)
    label = CharField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "bots"


class BotContextEntity(BaseModel):
    bot_id = ForeignKeyField(BotEntity, on_delete="CASCADE", unique=True)
    mode = IntegerField(index=True)
    strategy_name = CharField(index=True)
    strategy_args = TextField()
    source = CharField()
    symbol = CharField()
    timeframe = IntegerField(default=1)
    # memo: 本番稼働用
    account = ForeignKeyField(AccountEntity, null=True)
    # memo: バックテスト用
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)

    class Meta:
        table_name = "bot_contexts"
        indexes = ((("source", "symbol"), False),)
