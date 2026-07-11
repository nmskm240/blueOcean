from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import backtrader as bt

from blueOcean.strategy.registry import get_strategy_definition
from blueOcean.strategy.models import StrategyConfig


@dataclass(frozen=True)
class RunnerEvent:
    kind: str
    occurred_at: datetime
    error: str | None = None


class SyntheticLiveData(bt.feed.DataBase):
    """Controllable paper feed used until the Redis closed-bar feed lands."""

    params = (
        ("stop_event", None),
        ("status_queue", None),
        ("interval_seconds", 0.25),
    )

    def __init__(self):
        super().__init__()
        self._next_at = 0.0
        self._bar_number = 0

    def islive(self):
        return True

    def haslivedata(self):
        return True

    def _load(self):
        if self.p.stop_event.is_set():
            return False
        now = time.monotonic()
        if now < self._next_at:
            time.sleep(min(0.05, self._next_at - now))
            return None
        self._next_at = now + self.p.interval_seconds
        self._bar_number += 1
        close = 100.0 + math.sin(self._bar_number / 5.0)
        timestamp = datetime.now(timezone.utc)
        self.lines.datetime[0] = bt.date2num(timestamp)
        self.lines.open[0] = close
        self.lines.high[0] = close + 0.1
        self.lines.low[0] = close - 0.1
        self.lines.close[0] = close
        self.lines.volume[0] = 1
        self.lines.openinterest[0] = 0
        self.p.status_queue.put(RunnerEvent("heartbeat", timestamp))
        return True


def run_backtrader_strategy(
    config: StrategyConfig,
    stop_event,
    status_queue,
) -> None:
    """Build and run one real Backtrader Strategy instance in a child process."""
    try:
        if config.mode != "paper":
            raise RuntimeError("demo/live実行は注文Gateway実装後に利用できます")
        definition = get_strategy_definition(config.definition_key)
        cerebro = bt.Cerebro(stdstats=False, quicknotify=True)
        cerebro.adddata(
            SyntheticLiveData(
                stop_event=stop_event,
                status_queue=status_queue,
            )
        )
        cerebro.addstrategy(definition.strategy_class, **config.parameters)
        status_queue.put(RunnerEvent("running", datetime.now(timezone.utc)))
        cerebro.run(runonce=False, preload=False)
        status_queue.put(RunnerEvent("stopped", datetime.now(timezone.utc)))
    except Exception as exc:
        status_queue.put(
            RunnerEvent("error", datetime.now(timezone.utc), error=str(exc))
        )
