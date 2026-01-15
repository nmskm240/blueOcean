from __future__ import annotations

from datetime import datetime

from peewee import (
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
    # memo: バックテスト用
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)

    class Meta:
        table_name = "bot_contexts"
        indexes = ((("source", "symbol"), False),)
