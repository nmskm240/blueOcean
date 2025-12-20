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
    BotContextEntity,
    BotEntity,
    proxy,
)
from blueOcean.infra.database.mapper import to_domain, to_entity
from blueOcean.shared.registries import StrategyRegistry


@pytest.fixture
def db():
    db = SqliteDatabase(":memory:", pragmas={"foreign_keys": 1})
    proxy.initialize(db)
    db.create_tables([AccountEntity, BotEntity, BotContextEntity])
    try:
        yield db
    finally:
        db.drop_tables([AccountEntity, BotEntity, BotContextEntity])
        db.close()


@pytest.fixture(autouse=True)
def reset_strategy_registry():
    original_name_to_cls = StrategyRegistry._name_to_cls.copy()
    original_cls_to_name = StrategyRegistry._cls_to_name.copy()
    yield
    StrategyRegistry._name_to_cls = original_name_to_cls
    StrategyRegistry._cls_to_name = original_cls_to_name


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
        id=AccountId("acc-1"),
        credential=ApiCredential(
            exchange="binance",
            key="key",
            secret="secret",
            is_sandbox=True,
        ),
        label="acc1",
    )
    entity = to_entity(domain_account)
    restored = to_domain(entity)

    assert restored.id.value == entity.id
    assert restored.credential.exchange == "binance"
    assert restored.credential.key == "key"
    assert restored.credential.secret == "secret"
    assert restored.credential.is_sandbox is True
    assert restored.label == "acc1"


def test_account_entity_to_domain(account: AccountEntity):
    domain_account = to_domain(account)

    assert domain_account.id.value == "acc-1"
    assert domain_account.credential.exchange == "binance"
    assert domain_account.credential.key == "key"
    assert domain_account.credential.secret == "secret"
    assert domain_account.credential.is_sandbox is True
    assert domain_account.label == "test-account"


def test_account_to_entity():
    domain_account = Account(
        id=AccountId("acc-2"),
        credential=ApiCredential(
            exchange="bybit",
            key="key-2",
            secret="secret-2",
            is_sandbox=False,
        ),
        label="acc-2",
    )

    entity = to_entity(domain_account)

    assert entity.id == "acc-2"
    assert entity.exchange_name == "bybit"
    assert entity.api_key == "key-2"
    assert entity.api_secret == "secret-2"
    assert entity.is_sandbox is False
    assert entity.label == "acc-2"


def test_live_to_domain(account: AccountEntity):
    @StrategyRegistry.register("MyStrategy")
    class MyStrategy:
        pass

    bot_entity = BotEntity.create(
        id="live-1",
        pid=123,
        status=int(BotStatus.RUNNING),
        label="live-1",
        started_at=datetime(2024, 1, 1),
    )
    context_entity = BotContextEntity.create(
        bot_id=bot_entity,
        mode=int(BotRunMode.LIVE),
        strategy_name="MyStrategy",
        strategy_args='{"foo": 1}',
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=int(Timeframe.ONE_MINUTE),
        account=account,
    )

    bot = to_domain(bot_entity, context_entity)

    assert bot.id.value == "live-1"
    assert bot.context.mode is BotRunMode.LIVE
    assert bot.status is BotStatus.RUNNING
    assert bot.context.strategy_cls is MyStrategy
    assert bot.context.strategy_args == {"foo": 1}
    assert bot.context.symbol == "BTC/USDT"
    assert bot.context.source == account.exchange_name
    assert bot.context.account_id.value == account.id
    assert bot.pid == 123
    assert bot.started_at == datetime(2024, 1, 1)
    assert bot.label == "live-1"


def test_live_from_domain(account: AccountEntity):
    @StrategyRegistry.register("MyStrategy")
    class MyStrategy:
        pass

    ctx = LiveContext(
        strategy_cls=MyStrategy,
        strategy_args={"foo": 1},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
    )
    session = Bot(
        id=BotId("live-2"),
        status=BotStatus.STOPPED,
        context=ctx,
        worker=None,
        pid=456,
        started_at=datetime(2024, 1, 2),
        finished_at=datetime(2024, 1, 3),
        label="live-2",
    )

    bot_entity, context_entity = to_entity(session)

    assert bot_entity.id == "live-2"
    assert bot_entity.pid == 456
    assert bot_entity.status == int(BotStatus.STOPPED)
    assert bot_entity.started_at == datetime(2024, 1, 2)
    assert bot_entity.finished_at == datetime(2024, 1, 3)
    assert context_entity.strategy_name == "MyStrategy"
    assert context_entity.strategy_args == '{"foo": 1}'
    assert context_entity.account_id == account.id
    assert context_entity.symbol == "BTC/USDT"
    assert context_entity.timeframe == int(Timeframe.ONE_MINUTE)


def test_backtest_to_domain(db):
    @StrategyRegistry.register("BT")
    class BacktestStrategy:
        pass

    bot_entity = BotEntity.create(
        id="bt-1",
        status=int(BotStatus.RUNNING),
        label="bt-1",
    )
    context_entity = BotContextEntity.create(
        bot_id=bot_entity,
        mode=int(BotRunMode.BACKTEST),
        strategy_name="BT",
        strategy_args='{"p": 10}',
        source="binance",
        symbol="ETH/USDT",
        timeframe=int(Timeframe.FIFTEEN_MINUTE),
        started_at=datetime(2020, 1, 1),
        finished_at=datetime(2020, 1, 2),
    )

    bot = to_domain(bot_entity, context_entity)

    assert bot.id.value == "bt-1"
    assert bot.context.mode is BotRunMode.BACKTEST
    assert bot.context.strategy_cls is BacktestStrategy
    assert bot.context.strategy_args == {"p": 10}
    assert bot.context.source == "binance"
    assert bot.context.symbol == "ETH/USDT"
    assert bot.context.timeframe == Timeframe.FIFTEEN_MINUTE
    assert bot.context.start_at == datetime(2020, 1, 1)
    assert bot.context.end_at == datetime(2020, 1, 2)


def test_backtest_from_domain():
    @StrategyRegistry.register("BT")
    class BacktestStrategy:
        pass

    ctx = BacktestContext(
        strategy_cls=BacktestStrategy,
        strategy_args={"p": 10},
        source="binance",
        symbol="ETH/USDT",
        timeframe=Timeframe.FIFTEEN_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )
    bot = Bot(
        id=BotId("bt-2"),
        status=BotStatus.STOPPED,
        context=ctx,
        worker=None,
        pid=None,
        started_at=datetime(2020, 1, 1),
        finished_at=datetime(2020, 1, 2),
        label="bt-2",
    )

    bot_entity, context_entity = to_entity(bot)

    assert bot_entity.id == "bt-2"
    assert bot_entity.status == int(BotStatus.STOPPED)
    assert bot_entity.label == "bt-2"
    assert context_entity.strategy_name == "BT"
    assert context_entity.strategy_args == '{"p": 10}'
    assert context_entity.source == "binance"
    assert context_entity.symbol == "ETH/USDT"
    assert context_entity.timeframe == int(Timeframe.FIFTEEN_MINUTE)
    assert context_entity.started_at == datetime(2020, 1, 1)
    assert context_entity.finished_at == datetime(2020, 1, 2)
