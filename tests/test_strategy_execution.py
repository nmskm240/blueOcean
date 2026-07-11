from threading import Event
from queue import Queue

import backtrader as bt

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
        mode="paper",
    )

    run_backtrader_strategy(config, stop_event, status_queue)
    events = []
    while not status_queue.empty():
        events.append(status_queue.get().kind)

    assert events[0] == "running"
    assert events.count("heartbeat") >= 5
    assert events[-1] == "stopped"


def test_runner_rejects_demo_until_order_gateway_exists():
    stop_event = Event()
    status_queue = Queue()
    config = StrategyConfig(
        name="Demo test",
        definition_key="dummy_heartbeat",
        account_id="account-1",
        symbol="EURUSD",
        timeframe="H1",
        mode="demo",
    )

    run_backtrader_strategy(config, stop_event, status_queue)

    assert status_queue.get().kind == "error"
