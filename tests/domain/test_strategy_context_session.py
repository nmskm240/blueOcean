from datetime import datetime

from cuid2 import Cuid

from blueOcean.domain.context import Context
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.domain.session import Session
from blueOcean.domain.strategy import StrategySnapshot, StrategySnapshotId


def test_session_rename():
    session = Session(name="old")
    session.rename("new")
    assert session.name == "new"


def test_context_defaults_and_ids():
    snapshot_id = StrategySnapshotId("snap-1")
    context = Context(
        strategy_snapshot_id=snapshot_id,
        strategy_args={"p": 1},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime(2024, 1, 1),
        end_at=datetime(2024, 1, 2),
    )

    assert context.id.value
    assert context.strategy_snapshot_id.value == "snap-1"
    assert context.strategy_args == {"p": 1}


def test_strategy_snapshot_defaults():
    snapshot = StrategySnapshot(name="SMA")
    assert snapshot.id.value
    assert snapshot.name == "SMA"
