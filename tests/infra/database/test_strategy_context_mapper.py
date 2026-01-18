import json
from datetime import datetime

from blueOcean.domain.ohlcv import Timeframe
from blueOcean.domain.session import Session, SessionId
from blueOcean.domain.strategy import StrategySnapshotId
from blueOcean.infra.database.entities import (
    ContextEntity,
    SessionEntity,
    StrategySnapshotEntity,
)
from blueOcean.infra.database.mapper import to_domain, to_entity


def test_strategy_snapshot_mapper_roundtrip():
    entity = StrategySnapshotEntity(id="snap-1", name="S1")
    domain = to_domain(entity)

    assert domain.id.value == "snap-1"
    assert domain.name == "S1"

    entity_back = to_entity(domain)
    assert entity_back.id == "snap-1"
    assert entity_back.name == "S1"


def test_context_mapper_roundtrip():
    entity = ContextEntity(
        id="ctx-1",
        strategy_snapshot="snap-1",
        source="binance",
        symbol="BTC/USDT",
        timeframe=int(Timeframe.ONE_MINUTE),
        started_at=datetime(2024, 1, 1),
        finished_at=datetime(2024, 1, 2),
        parameters_json=json.dumps({"args": {"p": 1}}),
    )

    domain = to_domain(entity)
    assert domain.strategy_snapshot_id.value == "snap-1"
    assert domain.strategy_args == {"p": 1}

    entity_back = to_entity(domain)
    assert entity_back.strategy_snapshot_id == "snap-1"
    assert json.loads(entity_back.parameters_json)["args"]["p"] == 1


def test_session_mapper_roundtrip():
    session = Session(id=SessionId("sess-1"), name="s1")
    entity = to_entity(session)
    assert entity.id == "sess-1"

    domain = to_domain(SessionEntity(id="sess-1", name="s1"))
    assert domain.id.value == "sess-1"
