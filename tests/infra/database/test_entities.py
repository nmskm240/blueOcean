from datetime import datetime

import pytest
from peewee import SqliteDatabase

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
from blueOcean.infra.database.entities import (
    AccountEntity,
    BotBacktestEntity,
    BotLiveEntity,
    proxy,
)


@pytest.fixture
def db():
    db = SqliteDatabase(":memory:", pragmas={"foreign_keys": 1})
    proxy.initialize(db)
    db.create_tables([AccountEntity, BotLiveEntity, BotBacktestEntity])
    try:
        yield db
    finally:
        db.drop_tables([AccountEntity, BotLiveEntity, BotBacktestEntity])
        db.close()


@pytest.fixture
def account(db) -> AccountEntity:
    # keep it simple: insert via create, use explicit id
    return AccountEntity.create(
        id="acc-1",
        api_key="key",
        api_secret="secret",
        exchange_name="binance",
        is_sandbox=True,
        label="test-account",
    )


def test_account_roundtrip():
    domain_account = Account(
        id=AccountId.empty(),
        credential=ApiCredential(
            exchange="binance",
            key="key",
            secret="secret",
            is_sandbox=True,
        ),
        label="acc1",
    )
    entity = AccountEntity.from_domain(domain_account)
    restored = entity.to_domain()

    assert restored.id.value == entity.id
    assert restored.credential.exchange == "binance"
    assert restored.credential.key == "key"
    assert restored.credential.secret == "secret"
    assert restored.credential.is_sandbox is True
    assert restored.label == "acc1"


def test_live_to_domain(account: AccountEntity):
    entity = BotLiveEntity.create(
        id="live-1",
        pid=123,
        status=int(BotStatus.RUNNING),
        strategy_name="MyStrategy",
        strategy_args='{"foo": 1}',
        account=account,
        symbol="BTC/USDT",
        timeframe=int(Timeframe.ONE_MINUTE),
        label="live-1",
        started_at=datetime(2024, 1, 1),
        finished_at=None,
    )

    session = entity.to_domain()

    assert session.id.value == "live-1"
    assert session.mode is BotRunMode.LIVE
    assert session.status is BotStatus.RUNNING
    assert session.context.strategy_name == "MyStrategy"
    assert session.context.strategy_args == {"foo": 1}
    assert session.context.symbol == "BTC/USDT"
    assert session.context.source == account.exchange_name
    assert session.context.account_id.value == account.id
    assert session.context.pid == 123
    assert session.started_at == datetime(2024, 1, 1)
    assert session.label == "live-1"


def test_live_from_domain(account: AccountEntity):
    ctx = LiveContext(
        strategy_name="MyStrategy",
        strategy_args={"foo": 1},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
        pid=456,
    )
    session = Bot(
        id=BotId("live-2"),
        status=BotStatus.STOPPED,
        context=ctx,
        started_at=datetime(2024, 1, 2),
        finished_at=datetime(2024, 1, 3),
        label="live-2",
    )

    entity = BotLiveEntity.from_domain(session)

    assert entity.id == "live-2"
    assert entity.pid == 456
    assert entity.status == int(BotStatus.STOPPED)
    assert entity.strategy_name == "MyStrategy"
    assert entity.strategy_args == '{"foo": 1}'
    assert entity.account.id == account.id
    assert entity.symbol == "BTC/USDT"
    assert entity.timeframe == int(Timeframe.ONE_MINUTE)
    assert entity.started_at == datetime(2024, 1, 2)
    assert entity.finished_at == datetime(2024, 1, 3)


def test_backtest_to_domain(db):
    entity = BotBacktestEntity.create(
        id="bt-1",
        strategy_name="BT",
        strategy_args='{"p": 10}',
        source="binance",
        symbol="ETH/USDT",
        timeframe=int(Timeframe.FIFTEEN_MINUTE),
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
        status=int(BotStatus.RUNNING),
        label="bt-1",
    )

    session = entity.to_domain()

    assert session.id.value == "bt-1"
    assert session.mode is BotRunMode.BACKTEST
    assert session.context.strategy_name == "BT"
    assert session.context.strategy_args == {"p": 10}
    assert session.context.source == "binance"
    assert session.context.symbol == "ETH/USDT"
    assert session.context.timeframe == Timeframe.FIFTEEN_MINUTE
    assert session.context.start_at == datetime(2020, 1, 1)
    assert session.context.end_at == datetime(2020, 1, 2)


def test_backtest_from_domain():
    ctx = BacktestContext(
        strategy_name="BT",
        strategy_args={"p": 10},
        source="binance",
        symbol="ETH/USDT",
        timeframe=Timeframe.FIFTEEN_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )
    session = Bot(
        id=BotId("bt-2"),
        status=BotStatus.STOPPED,
        context=ctx,
        started_at=datetime(2020, 1, 1),
        finished_at=datetime(2020, 1, 2),
        label="bt-2",
    )

    entity = BotBacktestEntity.from_domain(session)

    assert entity.id == "bt-2"
    assert entity.strategy_name == "BT"
    assert entity.strategy_args == '{"p": 10}'
    assert entity.source == "binance"
    assert entity.symbol == "ETH/USDT"
    assert entity.timeframe == int(Timeframe.FIFTEEN_MINUTE)
    assert entity.start_at == datetime(2020, 1, 1)
    assert entity.end_at == datetime(2020, 1, 2)
    assert entity.status == int(BotStatus.STOPPED)
    assert entity.label == "bt-2"
