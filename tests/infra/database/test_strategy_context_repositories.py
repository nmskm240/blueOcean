from datetime import datetime

import pytest

from blueOcean.domain.context import Context, ContextId
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.domain.session import Session, SessionId
from blueOcean.domain.strategy import StrategySnapshot, StrategySnapshotId
from blueOcean.infra.database.entities import SessionContextEntity
from blueOcean.infra.database.repositories import (
    ContextRepository,
    SessionRepository,
    StrategySnapshotRepository,
)
def test_strategy_snapshot_repository_roundtrip(database):
    repo = StrategySnapshotRepository(connection=database)
    snapshot = StrategySnapshot(id=StrategySnapshotId("snap-1"), name="S1")

    repo.save(snapshot)
    fetched = repo.find_by_id(snapshot.id)

    assert fetched.id.value == "snap-1"
    assert fetched.name == "S1"


def test_context_repository_roundtrip(database):
    snapshot_repo = StrategySnapshotRepository(connection=database)
    context_repo = ContextRepository(connection=database)
    snapshot = StrategySnapshot(id=StrategySnapshotId("snap-1"), name="S1")
    snapshot_repo.save(snapshot)

    context = Context(
        id=ContextId("ctx-1"),
        strategy_snapshot_id=snapshot.id,
        strategy_args={"p": 1},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime(2024, 1, 1),
        end_at=datetime(2024, 1, 2),
    )
    context_repo.save(context)

    fetched = context_repo.find_by_id(context.id)
    assert fetched.strategy_snapshot_id.value == "snap-1"
    assert fetched.strategy_args == {"p": 1}


def test_context_find_by_session_id(database):
    session_repo = SessionRepository(connection=database)
    snapshot_repo = StrategySnapshotRepository(connection=database)
    context_repo = ContextRepository(connection=database)

    session = Session(id=SessionId("sess-1"), name="s1")
    session_repo.save(session)

    snapshot = StrategySnapshot(id=StrategySnapshotId("snap-1"), name="S1")
    snapshot_repo.save(snapshot)

    context = Context(
        id=ContextId("ctx-1"),
        strategy_snapshot_id=snapshot.id,
        strategy_args={"p": 1},
        source="binance",
        symbol="BTC/USDT",
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime(2024, 1, 1),
        end_at=datetime(2024, 1, 2),
    )
    context_repo.save(context)

    SessionContextEntity.create(session_id="sess-1", context_id="ctx-1")

    results = context_repo.find_by_session_id(session.id)
    assert [c.id.value for c in results] == ["ctx-1"]


def test_session_repository_roundtrip(database):
    repo = SessionRepository(connection=database)
    session = Session(id=SessionId("sess-2"), name="s2")

    repo.save(session)
    fetched = repo.find_by_id(session.id)

    assert fetched.id.value == "sess-2"
    assert fetched.name == "s2"
