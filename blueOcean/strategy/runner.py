from __future__ import annotations

from datetime import datetime, timezone

import backtrader as bt

from blueOcean.strategy.adapters import EXECUTION_BACKENDS, MARKET_DATA_SOURCES
from blueOcean.strategy.events import RunnerEvent
from blueOcean.strategy.registry import get_strategy_definition
from blueOcean.strategy.models import StrategyConfig


def run_backtrader_strategy(
    config: StrategyConfig,
    stop_event,
    status_queue,
) -> None:
    """Build and run one real Backtrader Strategy instance in a child process."""
    try:
        definition = get_strategy_definition(config.definition_key)
        data_source = MARKET_DATA_SOURCES[config.data_source]()
        execution = EXECUTION_BACKENDS[config.execution_backend]()
        cerebro = bt.Cerebro(stdstats=False, quicknotify=True)
        cerebro.adddata(data_source.create_feed(config, stop_event, status_queue))
        execution.configure(cerebro, config)
        cerebro.addstrategy(definition.strategy_class, **config.parameters)
        status_queue.put(RunnerEvent("running", datetime.now(timezone.utc)))
        strategies = cerebro.run(
            runonce=config.data_source != "synthetic",
            preload=config.data_source != "synthetic",
        )
        status_queue.put(
            RunnerEvent(
                "stopped",
                datetime.now(timezone.utc),
                result=execution.result(cerebro, strategies),
            )
        )
    except Exception as exc:
        status_queue.put(
            RunnerEvent("error", datetime.now(timezone.utc), error=str(exc))
        )
