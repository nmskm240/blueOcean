from datetime import datetime

from blueOcean.domain.account import AccountId
from blueOcean.domain.bot import (
    BacktestContext,
    Bot,
    BotRunMode,
    BotStatus,
    LiveContext,
)
from blueOcean.domain.ohlcv import Timeframe


class DummyWorker:
    def __init__(self, pid: int = 123):
        self.pid = pid
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def _build_live_context() -> LiveContext:
    return LiveContext(
        strategy_cls=object,
        strategy_args={"p": 1},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        account_id=AccountId("acc-1"),
    )


def test_create():
    context = _build_live_context()
    bot = Bot.create(context)

    assert isinstance(bot.id.value, str)
    assert bot.status is BotStatus.NONE
    assert bot.context is context
    assert bot.worker is None
    assert bot.pid is None
    assert bot.started_at is None
    assert bot.finished_at is None
    assert bot.label is None


def test_start_stop():
    context = _build_live_context()
    bot = Bot.create(context)
    worker = DummyWorker(pid=456)

    bot.attach(worker)
    bot.start()

    assert worker.started is True
    assert bot.pid == 456
    assert bot.started_at is not None
    assert bot.status is BotStatus.RUNNING

    bot.stop()

    assert worker.stopped is True
    assert bot.pid is None
    assert bot.finished_at is not None
    assert bot.status is BotStatus.STOPPED


def test_rename():
    bot = Bot.create(_build_live_context())
    bot.rename("bot-1")

    assert bot.label == "bot-1"


def test_mode():
    live_ctx = _build_live_context()
    backtest_ctx = BacktestContext(
        strategy_cls=object,
        strategy_args={"p": 2},
        source="binance",
        symbol="ETH/USDT",
        timeframe=Timeframe.FIFTEEN_MINUTE,
        start_at=datetime(2020, 1, 1),
        end_at=datetime(2020, 1, 2),
    )

    assert live_ctx.mode is BotRunMode.LIVE
    assert backtest_ctx.mode is BotRunMode.BACKTEST
