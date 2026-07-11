"""Backtrader strategies available to StrategyConfig.

Add a new strategy by defining a ``bt.Strategy`` subclass and decorating it
with ``register_strategy``. The UI, API validation and runner discover it from
the same registry.
"""

import backtrader as bt

from blueOcean.strategy.definitions import ParameterDefinition, register_strategy


@register_strategy(
    key="dummy_heartbeat",
    label="Dummy Heartbeat",
    parameters=(),
)
class DummyHeartbeatStrategy(bt.Strategy):
    """Minimal executable strategy used to verify the live run lifecycle."""

    def next(self):
        pass


@register_strategy(
    key="moving_average_cross",
    label="移動平均クロス",
    parameters=(
        ParameterDefinition("fast_period", "短期期間", int, 20, 1),
        ParameterDefinition("slow_period", "長期期間", int, 50, 2),
    ),
)
class MovingAverageCrossStrategy(bt.Strategy):
    params = (
        ("fast_period", 20),
        ("slow_period", 50),
    )

    def __init__(self):
        if self.p.fast_period >= self.p.slow_period:
            raise ValueError("短期期間は長期期間より小さくしてください")
        fast = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.fast_period)
        slow = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.slow_period)
        self.cross = bt.indicators.CrossOver(fast, slow)

    def next(self):
        if not self.position and self.cross > 0:
            self.buy()
        elif self.position and self.cross < 0:
            self.close()
