import json
from dataclasses import replace
from datetime import datetime, timezone

from blueOcean.strategy.models import (
    StrategyConfig,
    StrategyNotFoundError,
    StrategyRun,
    StrategyRunNotFoundError,
)
from blueOcean.strategy.schemas import StrategyRunSchema, StrategySchema


class StrategyRepository:
    def list(self) -> list[StrategyConfig]:
        return [row.to_entity() for row in StrategySchema.select().order_by(StrategySchema.name)]

    def get(self, strategy_id: str) -> StrategyConfig:
        row = StrategySchema.get_or_none(StrategySchema.id == strategy_id)
        if row is None:
            raise StrategyNotFoundError("Strategy not found")
        return row.to_entity()

    def save(self, strategy: StrategyConfig) -> StrategyConfig:
        values = {
            "name": strategy.name,
            "definition_key": strategy.definition_key,
            "account": strategy.account_id,
            "symbol": strategy.symbol,
            "timeframe": strategy.timeframe,
            "mode": strategy.mode,
            "parameters_json": json.dumps(strategy.parameters, ensure_ascii=False),
            "updated_at": datetime.now(timezone.utc),
        }
        StrategySchema.insert(id=strategy.id, **values).on_conflict(
            conflict_target=[StrategySchema.id],
            update=values,
        ).execute()
        return self.get(strategy.id)


class StrategyRunRepository:
    ACTIVE_STATES = ("starting", "warming", "running", "stopping")

    def list(self) -> list[StrategyRun]:
        query = StrategyRunSchema.select().order_by(StrategyRunSchema.started_at.desc())
        return [row.to_entity() for row in query]

    def get(self, run_id: str) -> StrategyRun:
        row = StrategyRunSchema.get_or_none(StrategyRunSchema.id == run_id)
        if row is None:
            raise StrategyRunNotFoundError("Strategy run not found")
        return row.to_entity()

    def active_for_strategy(self, strategy_id: str) -> StrategyRun | None:
        row = (
            StrategyRunSchema.select()
            .where(
                (StrategyRunSchema.strategy == strategy_id)
                & (StrategyRunSchema.state.in_(self.ACTIVE_STATES))
            )
            .order_by(StrategyRunSchema.started_at.desc())
            .first()
        )
        return row.to_entity() if row else None

    def save(self, run: StrategyRun) -> StrategyRun:
        values = {
            "strategy": run.strategy_id,
            "state": run.state,
            "pid": run.pid,
            "error": run.error,
            "started_at": run.started_at,
            "heartbeat_at": run.heartbeat_at,
            "stopped_at": run.stopped_at,
        }
        StrategyRunSchema.insert(id=run.id, **values).on_conflict(
            conflict_target=[StrategyRunSchema.id], update=values
        ).execute()
        return self.get(run.id)

    def update(self, run_id: str, **changes) -> StrategyRun:
        return self.save(replace(self.get(run_id), **changes))

    def mark_active_lost(self) -> None:
        StrategyRunSchema.update(
            state="lost",
            pid=None,
            error="Application restarted while the run was active",
            stopped_at=datetime.now(timezone.utc),
        ).where(StrategyRunSchema.state.in_(self.ACTIVE_STATES)).execute()
