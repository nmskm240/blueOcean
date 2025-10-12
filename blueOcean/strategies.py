from __future__ import annotations
import backtrader as bt
from . import indicators


class MACross(bt.Strategy):
    def __init__(self, short_length, long_length, angle_period=1, angle_threshold=15):
        if long_length <= short_length:
            raise ValueError("long_length must be greater than short_length")

        self.short_sma = bt.indicators.SMA(self.data, period=short_length)
        self.long_sma = bt.indicators.SMA(self.data, period=long_length)
        self.crossover = bt.indicators.CrossOver(self.short_sma, self.long_sma)
        self.angle = indicators.CrossAngle(self.short_sma, self.long_sma)
        self.angle_threshold = angle_threshold

    def next(self):
        if self.crossover[0] > 0:
            if self.position:
                self.close()
            if self.angle[0] >= self.angle_threshold:
                self.buy()

        elif self.crossover[0] < 0:
            if self.position:
                self.close()
            if self.angle[0] >= self.angle_threshold:
                self.sell()
