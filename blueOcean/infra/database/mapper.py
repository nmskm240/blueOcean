import json
from datetime import datetime
from typing import overload

from blueOcean.domain.context import Context, ContextId
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.domain.session import Session, SessionId
from blueOcean.domain.strategy import (
    ParameterType,
    StrategyArgs,
    StrategySnapshot,
    StrategySnapshotId,
)
from blueOcean.infra.database.entities import (
    ContextEntity,
    SessionEntity,
    StrategySnapshotEntity,
)


@overload
def to_domain(entity: SessionEntity) -> Session: ...


@overload
def to_domain(entity: ContextEntity) -> Context: ...


@overload
def to_domain(entity: StrategySnapshotEntity) -> StrategySnapshot: ...


def to_domain(*args):
    if len(args) == 1 and isinstance(args[0], SessionEntity):
        return Session(
            id=SessionId(value=args[0].id),
            name=args[0].name,
        )
    if len(args) == 1 and isinstance(args[0], ContextEntity):
        params: dict[str, ParameterType] = json.loads(args[0].parameters_json).get(
            "args", {}
        )
        return Context(
            id=ContextId(value=args[0].id),
            strategy_snapshot_id=StrategySnapshotId(value=args[0].strategy_snapshot_id),
            strategy_args=StrategyArgs(params),
            source=args[0].source,
            symbol=args[0].symbol,
            timeframe=Timeframe.from_compression(args[0].timeframe),
            start_at=args[0].started_at,
            end_at=args[0].finished_at,
        )
    if len(args) == 1 and isinstance(args[0], StrategySnapshotEntity):
        return StrategySnapshot(
            id=StrategySnapshotId(value=args[0].id),
            name=args[0].name,
        )
    raise NotImplementedError()


@overload
def to_entity(session: Session) -> SessionEntity: ...


@overload
def to_entity(entity: Context) -> ContextEntity: ...


@overload
def to_entity(entity: StrategySnapshot) -> StrategySnapshotEntity: ...


def to_entity(*args):
    if len(args) == 1 and isinstance(args[0], Session):
        return SessionEntity(
            id=args[0].id.value,
            name=args[0].name,
        )
    if len(args) == 1 and isinstance(args[0], Context):
        return ContextEntity(
            id=args[0].id.value,
            strategy_snapshot=args[0].strategy_snapshot_id.value,
            source=args[0].source,
            symbol=args[0].symbol,
            timeframe=args[0].timeframe.value,
            started_at=args[0].start_at,
            finished_at=args[0].end_at,
            parameters_json=json.dumps({"args": args[0].strategy_args}),
        )
    if len(args) == 1 and isinstance(args[0], StrategySnapshot):
        return StrategySnapshotEntity(
            id=args[0].id.value,
            name=args[0].name,
        )
    raise NotImplementedError()
