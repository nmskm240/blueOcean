from __future__ import annotations

import json
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

from blueOcean.domain.account import Account, AccountId, ApiCredential
from blueOcean.domain.bot import (
    BacktestContext,
    Bot,
    BotId,
    BotRunMode,
    BotStatus,
    LiveContext,
)
from blueOcean.domain.ohlcv import Timeframe

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
            id=AccountId(self.id),
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
        entity = cls(
            api_key=account.credential.key,
            api_secret=account.credential.secret,
            exchange_name=account.credential.exchange,
            is_sandbox=account.credential.is_sandbox,
            label=account.label,
            updated_at=datetime.now(),
        )

        if not account.id.is_empty:
            entity.id = account.id.value

        return entity


class BotLiveEntity(BaseModel):
    id = CharField(primary_key=True, default=lambda: cuid2.Cuid().generate())
    pid = IntegerField()
    status = SmallIntegerField()
    strategy_name = CharField()
    strategy_args = TextField()
    account = ForeignKeyField(AccountEntity, backref="live_bots")
    symbol = CharField()
    timeframe = IntegerField(default=1)
    label = CharField(null=True)
    started_at = DateTimeField()
    finished_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "bot_lives"

    def to_domain(self) -> Bot:
        try:
            strategy_args: dict[str, object] = json.loads(self.strategy_args or "{}")
        except json.JSONDecodeError:
            strategy_args = {}

        context = LiveContext(
            strategy_name=self.strategy_name,
            strategy_args=strategy_args,
            symbol=self.symbol,
            source=self.account.exchange_name,
            timeframe=Timeframe.from_compression(self.timeframe),
            account_id=AccountId(self.account.id),
            pid=self.pid,
        )

        return Bot(
            id=BotId(self.id),
            status=BotStatus(self.status),
            context=context,
            started_at=self.started_at,
            finished_at=self.finished_at,
            label=self.label,
        )

    @classmethod
    def from_domain(cls, bot: Bot) -> BotLiveEntity:
        if bot.mode is not BotRunMode.LIVE:
            ValueError("Expected LIVE bot")

        entity = cls(
            pid=bot.context.pid,
            status=bot.status.value,
            strategy_name=bot.context.strategy_name,
            strategy_args=json.dumps(bot.context.strategy_args, ensure_ascii=False),
            account=bot.context.account_id.value,
            symbol=bot.context.symbol,
            timeframe=bot.context.timeframe.value,
            label=bot.label,
            started_at=bot.started_at,
            finished_at=bot.finished_at,
        )

        if not bot.id.is_empty:
            entity.id = bot.id.value

        return entity


class BotBacktestEntity(BaseModel):
    id = CharField(primary_key=True, default=lambda: cuid2.Cuid().generate())
    strategy_name = CharField()
    strategy_args = TextField()
    source = CharField()
    symbol = CharField()
    timeframe = IntegerField(default=1)
    start_at = DateTimeField()
    end_at = DateTimeField()
    status = SmallIntegerField()
    label = CharField()
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "bot_backtests"

    def to_domain(self) -> Bot:
        try:
            strategy_args: dict[str, object] = json.loads(self.strategy_args or "{}")
        except json.JSONDecodeError:
            strategy_args = {}

        context = BacktestContext(
            strategy_name=self.strategy_name,
            strategy_args=strategy_args,
            symbol=self.symbol,
            timeframe=Timeframe.from_compression(self.timeframe),
            source=self.source,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        return Bot(
            id=BotId(self.id),
            status=BotStatus(self.status),
            context=context,
            started_at=None,
            finished_at=None,
            label=self.label,
        )

    @classmethod
    def from_domain(cls, bot: Bot) -> BotBacktestEntity:
        if bot.mode is not BotRunMode.BACKTEST:
            ValueError("Expected BACKTEST bot")

        entity = cls(
            status=bot.status.value,
            strategy_name=bot.context.strategy_name,
            strategy_args=json.dumps(bot.context.strategy_args, ensure_ascii=False),
            source=bot.context.source,
            symbol=bot.context.symbol,
            timeframe=bot.context.timeframe.value,
            label=bot.label,
            start_at=bot.context.start_at,
            end_at=bot.context.end_at,
        )

        if not bot.id.is_empty:
            entity.id = bot.id.value

        return entity
