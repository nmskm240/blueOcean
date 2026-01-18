from datetime import datetime

import pytest
from peewee import IntegrityError

from blueOcean.infra.database.entities import (
    ContextEntity,
    SessionContextEntity,
    SessionEntity,
    StrategySnapshotEntity,
)
def test_context_entity_with_snapshot(database):
    snapshot = StrategySnapshotEntity.create(id="snap-1", name="S1")
    context = ContextEntity.create(
        id="ctx-1",
        strategy_snapshot=snapshot,
        source="binance",
        symbol="BTC/USDT",
        timeframe=1,
        started_at=datetime(2024, 1, 1),
        finished_at=datetime(2024, 1, 2),
        parameters_json='{"args": {"p": 1}}',
    )

    assert context.strategy_snapshot_id == "snap-1"


def test_session_context_link(database):
    snapshot = StrategySnapshotEntity.create(id="snap-1", name="S1")
    context = ContextEntity.create(
        id="ctx-1",
        strategy_snapshot=snapshot,
        source="binance",
        symbol="BTC/USDT",
        timeframe=1,
        started_at=datetime(2024, 1, 1),
        finished_at=datetime(2024, 1, 2),
        parameters_json='{"args": {"p": 1}}',
    )
    session = SessionEntity.create(id="sess-1", name="s1")
    link = SessionContextEntity.create(session_id=session, context_id=context)

    assert link.session_id.id == "sess-1"
    assert link.context_id.id == "ctx-1"


def test_context_entity_requires_snapshot(database):
    with pytest.raises(IntegrityError):
        ContextEntity.create(
            id="ctx-2",
            strategy_snapshot="missing",
            source="binance",
            symbol="BTC/USDT",
            timeframe=1,
            started_at=datetime(2024, 1, 1),
            finished_at=datetime(2024, 1, 2),
            parameters_json='{"args": {"p": 1}}',
        )
