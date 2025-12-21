from datetime import datetime

import pytest

from blueOcean.domain.account import AccountId
from blueOcean.domain.bot import BacktestContext, BotId, LiveContext
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.application.services import BotWorkerFactory
from tests.dummy.workers import DummyBacktestWorker, DummyLiveWorker


def _live_context():
    return LiveContext(
        strategy_cls=object,
        strategy_args={},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId("acc-1"),
    )


def _backtest_context():
    return BacktestContext(
        strategy_cls=object,
        strategy_args={},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )


def test_live(monkeypatch):
    from blueOcean.application import workers

    monkeypatch.setattr(workers, "LiveTradeWorker", DummyLiveWorker)
    bot_id = BotId("bot-1")
    context = _live_context()

    factory = BotWorkerFactory()
    worker = factory.create(bot_id, context)

    assert isinstance(worker, DummyLiveWorker)
    assert worker.bot_id == bot_id
    assert worker.context is context


def test_backtest(monkeypatch):
    from blueOcean.application import workers

    monkeypatch.setattr(workers, "BacktestWorker", DummyBacktestWorker)
    bot_id = BotId("bot-2")
    context = _backtest_context()

    factory = BotWorkerFactory()
    worker = factory.create(bot_id, context)

    assert isinstance(worker, DummyBacktestWorker)
    assert worker.bot_id == bot_id
    assert worker.context is context


def test_unknown():
    class UnknownContext:
        mode = object()

    factory = BotWorkerFactory()
    with pytest.raises(RuntimeError):
        factory.create(BotId("bot-3"), UnknownContext())
