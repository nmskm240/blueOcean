from __future__ import annotations

from datetime import datetime

from peewee import (
    CharField,
    CompositeKey,
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


class SessionEntity(BaseModel):
    id = CharField(primary_key=True)
    name = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "sessions"


class StrategySnapshotEntity(BaseModel):
    id = CharField(primary_key=True)
    name = CharField()
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "strategy_snapshots"


class ContextEntity(BaseModel):
    id = CharField(primary_key=True)
    strategy_snapshot = ForeignKeyField(StrategySnapshotEntity, on_delete="RESTRICT")

    status = IntegerField(default=0)
    source = CharField()
    symbol = CharField()
    timeframe = IntegerField(default=1)
    started_at = DateTimeField()
    finished_at = DateTimeField()
    parameters_json = TextField()

    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "contexts"
        indexes = ((("source", "symbol"), False),)


class SessionContextEntity(BaseModel):
    session_id = ForeignKeyField(SessionEntity, on_delete="CASCADE")
    context_id = ForeignKeyField(ContextEntity, on_delete="CASCADE", unique=True)

    class Meta:
        table_name = "session_contexts"
        primary_key = CompositeKey("session_id", "context_id")


entities: list[type[Model]] = [
    SessionEntity,
    StrategySnapshotEntity,
    ContextEntity,
    SessionContextEntity,
]
