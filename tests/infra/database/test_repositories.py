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
from blueOcean.infra.database.entities import AccountEntity, proxy
from blueOcean.infra.database.repositories import AccountRepository, BotRepository


@pytest.fixture
def db():
    db = SqliteDatabase(":memory:", pragmas={"foreign_keys": 1})
    proxy.initialize(db)
    from blueOcean.infra.database.entities import BotBacktestEntity, BotLiveEntity

    db.create_tables([AccountEntity, BotLiveEntity, BotBacktestEntity])
    try:
        yield db
    finally:
        from blueOcean.infra.database.entities import BotBacktestEntity, BotLiveEntity

        db.drop_tables([AccountEntity, BotLiveEntity, BotBacktestEntity])
        db.close()


@pytest.fixture
def account_repo(db) -> AccountRepository:
    return AccountRepository(connection=db)


@pytest.fixture
def session_repo(db) -> BotRepository:
    return BotRepository(connection=db)


def _build_account(label: str = "acc") -> Account:
    faker = Faker()
    return Account(
        id=AccountId.empty(),
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
    assert not saved.id.is_empty

    fetched = account_repo.get_by_id(saved.id)
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
    fetched = account_repo.get_by_id(saved.id)
    assert fetched.label == "acc3-updated"
    assert fetched.credential.is_sandbox is False


def test_account_list_delete(account_repo: AccountRepository):
    acc1 = account_repo.save(_build_account("accA"))
    acc2 = account_repo.save(_build_account("accB"))

    ids = {a.id.value for a in account_repo.list()}
    assert acc1.id.value in ids
    assert acc2.id.value in ids

    account_repo.delete_by_id(acc1.id)
    remaining_ids = {a.id.value for a in account_repo.list()}
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


def test_session_save_live(session_repo: BotRepository, account: AccountEntity):
    context = LiveContext(
        strategy_name="MyStrategy",
        strategy_args={"foo": 1},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
        pid=1234,
    )

    session = Bot(
        id=BotId.empty(),
        status=BotStatus.RUNNING,
        context=context,
        started_at=datetime.now(),
        finished_at=None,
        label="live-1",
    )

    saved = session_repo.save(session)

    assert saved.id.value is not None
    assert saved.mode is BotRunMode.LIVE
    assert saved.context.strategy_name == "MyStrategy"
    assert saved.context.strategy_args == {"foo": 1}
    assert saved.context.symbol == "BTC/USDT"
    assert saved.context.source == "binance"
    assert saved.context.account_id.value == account.id
    assert saved.context.pid == 1234
    assert saved.label == "live-1"


def test_session_save_backtest(session_repo: BotRepository):
    context = BacktestContext(
        strategy_name="BacktestStrategy",
        strategy_args={"param": 10},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.FIFTEEN_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )

    session = Bot(
        id=BotId.empty(),
        status=BotStatus.RUNNING,
        context=context,
        started_at=datetime(2020, 1, 1),
        finished_at=None,
        label="bt-1",
    )

    saved = session_repo.save(session)

    assert saved.mode is BotRunMode.BACKTEST
    assert saved.context.strategy_name == "BacktestStrategy"
    assert saved.context.strategy_args == {"param": 10}
    assert saved.context.source == "binance"
    assert saved.context.symbol == "BTC/USDT"
    assert saved.context.timeframe == Timeframe.FIFTEEN_MINUTE
    assert saved.context.start_at == datetime(2020, 1, 1)
    assert saved.context.end_at == datetime(2020, 1, 2)
    assert saved.label == "bt-1"


def test_session_list(session_repo: BotRepository, account: AccountEntity):
    live_ctx = LiveContext(
        strategy_name="S1",
        strategy_args={},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
        pid=1,
    )
    live_session = Bot(
        id=BotId.empty(),
        status=BotStatus.RUNNING,
        context=live_ctx,
        started_at=datetime.now(),
        finished_at=None,
        label="live-1",
    )
    session_repo.save(live_session)

    bt_ctx = BacktestContext(
        strategy_name="S2",
        strategy_args={},
        source="binance",
        symbol="ETH/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )
    bt_session = Bot(
        id=BotId.empty(),
        status=BotStatus.RUNNING,
        context=bt_ctx,
        started_at=datetime(2020, 1, 1),
        finished_at=None,
        label="bt-1",
    )
    session_repo.save(bt_session)

    bots = session_repo.get_all()
    modes_by_label = {s.label: s.mode for s in bots}
    assert modes_by_label["live-1"] is BotRunMode.LIVE
    assert modes_by_label["bt-1"] is BotRunMode.BACKTEST


def test_session_update(session_repo: BotRepository, account: AccountEntity):
    ctx = LiveContext(
        strategy_name="UpdStrategy",
        strategy_args={"x": 1},
        source=account.exchange_name,
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId(account.id),
        pid=10,
    )
    session = Bot(
        id=BotId.empty(),
        status=BotStatus.RUNNING,
        context=ctx,
        started_at=datetime.now(),
        finished_at=None,
        label="upd",
    )
    saved1 = session_repo.save(session)

    updated_session = Bot(
        id=saved1.id,
        status=BotStatus.STOPPED,
        context=LiveContext(
            strategy_name=ctx.strategy_name,
            strategy_args=ctx.strategy_args,
            source=ctx.source,
            symbol=ctx.symbol,
            timeframe=ctx.timeframe,
            account_id=ctx.account_id,
            pid=20,
        ),
        started_at=saved1.started_at,
        finished_at=datetime.now(),
        label="upd",
    )

    saved2 = session_repo.save(updated_session)

    assert saved2.id.value == saved1.id.value
    assert saved2.status is BotStatus.STOPPED
    assert saved2.context.pid == 20

    bots = session_repo.get_all()
    upd = next(s for s in bots if s.label == "upd")
    assert upd.status is BotStatus.STOPPED
    assert upd.context.pid == 20
