import json
from datetime import datetime, timezone

from peewee import CharField, DateTimeField, FloatField, ForeignKeyField, IntegerField, Model, TextField

from blueOcean.database.schemas import AccountSchema, proxy
from blueOcean.strategy.models import StrategyConfig, StrategyRun


class StrategySchema(Model):
    id = CharField(primary_key=True)
    name = CharField(unique=True)
    definition_key = CharField(default="dummy_heartbeat")
    account = ForeignKeyField(
        AccountSchema, backref="strategies", on_delete="RESTRICT", null=True
    )
    symbol = CharField()
    timeframe = CharField()
    mode = CharField(default="paper")  # legacy column; remove after migration window
    data_source = CharField(default="synthetic")
    execution_backend = CharField(default="paper")
    history_period = CharField(default="1y")
    initial_cash = FloatField(default=100_000.0)
    commission = FloatField(default=0.001)
    parameters_json = TextField(default="{}")
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    class Meta:
        table_name = "strategies"
        database = proxy

    def to_entity(self) -> StrategyConfig:
        return StrategyConfig(
            id=self.id,
            name=self.name,
            definition_key=self.definition_key,
            account_id=self.account_id,
            symbol=self.symbol,
            timeframe=self.timeframe,
            data_source=self.data_source,
            execution_backend=self.execution_backend,
            history_period=self.history_period,
            initial_cash=self.initial_cash,
            commission=self.commission,
            parameters=json.loads(self.parameters_json),
        )


class StrategyRunSchema(Model):
    id = CharField(primary_key=True)
    strategy = ForeignKeyField(StrategySchema, backref="runs", on_delete="CASCADE")
    state = CharField()
    pid = IntegerField(null=True)
    error = TextField(null=True)
    started_at = DateTimeField()
    heartbeat_at = DateTimeField(null=True)
    stopped_at = DateTimeField(null=True)
    result_json = TextField(null=True)

    class Meta:
        table_name = "strategy_runs"
        database = proxy

    def to_entity(self) -> StrategyRun:
        return StrategyRun(
            id=self.id,
            strategy_id=self.strategy_id,
            state=self.state,
            pid=self.pid,
            error=self.error,
            started_at=self.started_at,
            heartbeat_at=self.heartbeat_at,
            stopped_at=self.stopped_at,
            result=json.loads(self.result_json) if self.result_json else None,
        )
