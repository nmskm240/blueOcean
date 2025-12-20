from datetime import datetime

import pytest
from faker import Faker
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
from blueOcean.infra.database.repositories import AccountRepository, BotRepository
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
def account_repo(db) -> AccountRepository:
    return AccountRepository(connection=db)


@pytest.fixture
def bot_repo(db) -> BotRepository:
    return BotRepository(connection=db)


def _build_account(label: str = "acc") -> Account:
    faker = Faker()
    return Account(
        id=AccountId.create(),
        credential=ApiCredential(
            exchange="binance",
            key=faker.lexify(text="????-????"),
            secret=faker.lexify(text="????-????"),
            is_sandbox=True,
        ),
        label=label,
    )


def test_account_save_get(account_repo: AccountRepository):
    acc = _build_account("acc2")
    saved = account_repo.save(acc)
    assert saved.id.value is not None

    fetched = account_repo.find_by_id(saved.id)
    assert fetched.label == "acc2"
    assert fetched.credential.exchange == "binance"


def test_account_update(account_repo: AccountRepository):
    acc = _build_account("acc3")
    saved = account_repo.save(acc)

    updated = Account(
        id=saved.id,
        credential=ApiCredential(
            exchange=saved.credential.exchange,
            key=saved.credential.key,
            secret=saved.credential.secret,
            is_sandbox=False,
        ),
        label="acc3-updated",
    )

    account_repo.save(updated)
    fetched = account_repo.find_by_id(saved.id)
    assert fetched.label == "acc3-updated"
    assert fetched.credential.is_sandbox is False


def test_account_list_delete(account_repo: AccountRepository):
    acc1 = account_repo.save(_build_account("accA"))
    acc2 = account_repo.save(_build_account("accB"))

    ids = {a.id.value for a in account_repo.get_all()}
    assert acc1.id.value in ids
    assert acc2.id.value in ids

    account_repo.delete_by_id(acc1.id)
    remaining_ids = {a.id.value for a in account_repo.get_all()}
    assert acc1.id.value not in remaining_ids
    assert acc2.id.value in remaining_ids


@pytest.fixture
def account(db) -> AccountEntity:
    return AccountEntity.create(
        id="account-1",
        api_key="key",
        api_secret="secret",
        exchange_name="binance",
        is_sandbox=True,
        label="test-account",
    )


def test_bot_save_live(bot_repo: BotRepository, account: AccountEntity):
    @StrategyRegistry.register("MyStrategy")
    class MyStrategy:
        pass

    context = LiveContext(
        strategy_cls=MyStrategy,
        strategy_args={"foo": 1},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
    )

    session = Bot(
        id=BotId.create(),
        status=BotStatus.RUNNING,
        context=context,
        worker=None,
        pid=1234,
        started_at=datetime.now(),
        finished_at=None,
        label="live-1",
    )

    saved = bot_repo.save(session)

    assert saved.id.value is not None
    assert saved.context.mode is BotRunMode.LIVE
    assert saved.context.strategy_cls is MyStrategy
    assert saved.context.strategy_args == {"foo": 1}
    assert saved.context.symbol == "BTC/USDT"
    assert saved.context.source == "binance"
    assert saved.context.account_id.value == account.id
    assert saved.pid == 1234
    assert saved.label == "live-1"


def test_bot_save_backtest(bot_repo: BotRepository):
    @StrategyRegistry.register("BacktestStrategy")
    class BacktestStrategy:
        pass

    context = BacktestContext(
        strategy_cls=BacktestStrategy,
        strategy_args={"param": 10},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.FIFTEEN_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )

    session = Bot(
        id=BotId.create(),
        status=BotStatus.RUNNING,
        context=context,
        worker=None,
        pid=None,
        started_at=datetime(2020, 1, 1),
        finished_at=None,
        label="bt-1",
    )

    saved = bot_repo.save(session)

    assert saved.context.mode is BotRunMode.BACKTEST
    assert saved.context.strategy_cls is BacktestStrategy
    assert saved.context.strategy_args == {"param": 10}
    assert saved.context.source == "binance"
    assert saved.context.symbol == "BTC/USDT"
    assert saved.context.timeframe == Timeframe.FIFTEEN_MINUTE
    assert saved.context.start_at == datetime(2020, 1, 1)
    assert saved.context.end_at == datetime(2020, 1, 2)
    assert saved.label == "bt-1"


def test_bot_list(bot_repo: BotRepository, account: AccountEntity):
    @StrategyRegistry.register("S1")
    class StrategyOne:
        pass

    @StrategyRegistry.register("S2")
    class StrategyTwo:
        pass

    live_ctx = LiveContext(
        strategy_cls=StrategyOne,
        strategy_args={},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
    )
    live_session = Bot(
        id=BotId.create(),
        status=BotStatus.RUNNING,
        context=live_ctx,
        worker=None,
        pid=1,
        started_at=datetime.now(),
        finished_at=None,
        label="live-1",
    )
    bot_repo.save(live_session)

    bt_ctx = BacktestContext(
        strategy_cls=StrategyTwo,
        strategy_args={},
        source="binance",
        symbol="ETH/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )
    bt_session = Bot(
        id=BotId.create(),
        status=BotStatus.RUNNING,
        context=bt_ctx,
        worker=None,
        pid=None,
        started_at=datetime(2020, 1, 1),
        finished_at=None,
        label="bt-1",
    )
    bot_repo.save(bt_session)

    bots = bot_repo.get_all()
    modes_by_label = {s.label: s.context.mode for s in bots}
    assert modes_by_label["live-1"] is BotRunMode.LIVE
    assert modes_by_label["bt-1"] is BotRunMode.BACKTEST


def test_bot_update(bot_repo: BotRepository, account: AccountEntity):
    @StrategyRegistry.register("UpdStrategy")
    class UpdStrategy:
        pass

    ctx = LiveContext(
        strategy_cls=UpdStrategy,
        strategy_args={"x": 1},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
    )
    session = Bot(
        id=BotId.create(),
        status=BotStatus.RUNNING,
        context=ctx,
        worker=None,
        pid=10,
        started_at=datetime.now(),
        finished_at=None,
        label="upd",
    )
    saved1 = bot_repo.save(session)

    updated_session = Bot(
        id=saved1.id,
        status=BotStatus.STOPPED,
        context=LiveContext(
            strategy_cls=ctx.strategy_cls,
            strategy_args=ctx.strategy_args,
            source=ctx.source,
            symbol=ctx.symbol,
            timeframe=ctx.timeframe,
            account_id=ctx.account_id,
        ),
        worker=None,
        pid=20,
        started_at=saved1.started_at,
        finished_at=datetime.now(),
        label="upd",
    )

    saved2 = bot_repo.save(updated_session)

    assert saved2.id.value == saved1.id.value
    assert saved2.status is BotStatus.STOPPED
    assert saved2.pid == 20

    bots = bot_repo.get_all()
    upd = next(s for s in bots if s.label == "upd")
    assert upd.status is BotStatus.STOPPED
    assert upd.pid == 20
