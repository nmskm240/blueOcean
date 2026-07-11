from threading import Event
from queue import Queue

import backtrader as bt
import pytest

from blueOcean.strategy.registry import get_strategy_definition
from blueOcean.strategy.implementations import MovingAverageCrossStrategy
from blueOcean.strategy.models import StrategyConfig
from blueOcean.strategy.runner import run_backtrader_strategy


class StopAfterHeartbeatsQueue(Queue):
    def __init__(self, stop_event, count=5):
        super().__init__()
        self.stop_event = stop_event
        self.remaining = count

    def put(self, item, *args, **kwargs):
        super().put(item, *args, **kwargs)
        if item.kind == "heartbeat":
            self.remaining -= 1
            if self.remaining <= 0:
                self.stop_event.set()


def test_registry_resolves_real_backtrader_strategy_class():
    definition = get_strategy_definition("moving_average_cross")

    assert definition.strategy_class is MovingAverageCrossStrategy
    assert issubclass(definition.strategy_class, bt.Strategy)


def test_runner_executes_backtrader_and_emits_heartbeats():
    stop_event = Event()
    status_queue = StopAfterHeartbeatsQueue(stop_event)
    config = StrategyConfig(
        name="Execution test",
        definition_key="dummy_heartbeat",
        account_id="account-1",
        symbol="EURUSD",
        timeframe="H1",
        data_source="synthetic",
        execution_backend="paper",
    )

    run_backtrader_strategy(config, stop_event, status_queue)
    events = []
    while not status_queue.empty():
        events.append(status_queue.get())

    assert events[0].kind == "running"
    assert sum(event.kind == "heartbeat" for event in events) >= 5
    assert events[-1].kind == "stopped"
    assert events[-1].result["equity_curve"]
    assert "max_drawdown_pct" in events[-1].result
    assert "net_profit" in events[-1].result


def test_strategy_config_rejects_unsupported_data_execution_pair():
    with pytest.raises(ValueError, match="組み合わせ"):
        StrategyConfig(
            name="Invalid pair",
            definition_key="dummy_heartbeat",
            account_id="account-1",
            symbol="EURUSD",
            timeframe="H1",
            data_source="yfinance",
            execution_backend="paper",
        )
