from datetime import datetime

import pytest
from peewee import SqliteDatabase

from blueOcean.application.services import BotExecutionService
from blueOcean.domain.account import AccountId
from blueOcean.domain.bot import Bot, BotId, BotStatus, LiveContext
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.infra.database.entities import (
    AccountEntity,
    BotContextEntity,
    BotEntity,
    proxy,
)
from blueOcean.infra.database.repositories import BotRepository
from blueOcean.shared.registries import StrategyRegistry
from tests.dummy.workers import DummyRecoverWorker, DummyWorker


class DummyFactory:
    def __init__(self, worker: DummyWorker):
        self.worker = worker
        self.calls = []

    def create(self, bot_id, context):
        self.calls.append((bot_id, context))
        return self.worker


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


@pytest.fixture
def bot_repo(db) -> BotRepository:
    AccountEntity.create(
        id="acc-1",
        api_key="key",
        api_secret="secret",
        exchange_name="binance",
        is_sandbox=True,
        label="test-account",
    )
    return BotRepository(connection=db)


@pytest.fixture(autouse=True)
def reset_strategy_registry():
    original_name_to_cls = StrategyRegistry._name_to_cls.copy()
    original_cls_to_name = StrategyRegistry._cls_to_name.copy()
    yield
    StrategyRegistry._name_to_cls = original_name_to_cls
    StrategyRegistry._cls_to_name = original_cls_to_name


def _live_context():
    @StrategyRegistry.register("TestStrategy")
    class TestStrategy:
        pass

    return LiveContext(
        strategy_cls=TestStrategy,
        strategy_args={},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId("acc-1"),
    )


def test_start(bot_repo):
    worker = DummyWorker()
    factory = DummyFactory(worker)

    service = BotExecutionService(bot_repository=bot_repo, bot_worker_factory=factory)
    bot_id = service.start(_live_context())

    assert bot_id.value is not None
    assert len(factory.calls) == 1
    called_id, called_context = factory.calls[0]
    assert called_id.value == bot_id.value
    assert called_context.source == "binance"
    assert worker.started is True
    saved = bot_repo.find_by_id(bot_id)
    assert saved.status is BotStatus.RUNNING
    assert saved.pid == 999


def test_stop(monkeypatch, bot_repo):
    monkeypatch.setattr("blueOcean.application.workers.RecoverWorker", DummyRecoverWorker)
    factory = DummyFactory(DummyWorker())
    service = BotExecutionService(bot_repository=bot_repo, bot_worker_factory=factory)

    context = _live_context()
    bot = Bot(
        id=BotId("bot-2"),
        status=BotStatus.RUNNING,
        context=context,
        worker=None,
        pid=123,
        started_at=datetime(2024, 1, 1),
        finished_at=None,
        label="live",
    )
    bot_repo.save(bot)

    service.stop(bot.id)

    saved = bot_repo.find_by_id(bot.id)
    assert saved.status is BotStatus.STOPPED
    assert saved.pid is None
    assert saved.finished_at is not None
